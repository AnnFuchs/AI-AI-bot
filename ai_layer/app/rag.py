import uuid
import logging
from typing import List, Optional, Dict, Any
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.config import settings
from app.llm import LLMHandler
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastembed import SparseTextEmbedding
from qdrant_client.http import models

logger = logging.getLogger(__name__)

HYDE_PROMPT = """Ты — невролог, пишешь фрагмент клинических рекомендаций для пациента после инсульта.
Напиши 3-4 предложения медицинским языком которые отвечают на вопрос пациента, перенесшего инсульт.
Используй медицинскую терминологию и аббревиатуры характерные для российских клинических рекомендаций.
Помни: ОНМК, инфаркт мозга, ишемический инсульт — это связанные понятия в контексте инсульта.
Только текст фрагмента, без вступлений и пояснений.

Вопрос: {query}"""

COSINE_SCORE_THRESHOLD = 0.55


class RAGService:
    def __init__(self, qdrant_client: AsyncQdrantClient, llm_handler: LLMHandler):
        self.qdrant_client = qdrant_client
        self.llm_handler = llm_handler
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def _get_hyde_vector(self, query: str) -> List[float]:
        try:
            messages = [{"role": "system", "content": HYDE_PROMPT.format(query=query)}]
            hypothetical_doc = await self.llm_handler.chat_completion(messages, temperature=0.0)
            logger.info(f"HyDE generated doc: {hypothetical_doc[:100]}...")
            return await self.llm_handler.get_embedding(hypothetical_doc)
        except Exception as e:
            logger.warning(f"HyDE failed, falling back to direct embedding: {e}")
            return await self.llm_handler.get_embedding(query)

    async def get_sparse_embedding(self, text: str) -> Dict[str, Any]:
        """Преобразует текст в разреженный вектор (indices и values)"""
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            self.executor,
            lambda: list(self.sparse_model.embed([text]))
        )
        vector = embeddings[0]
        return {
            "indices": vector.indices.tolist(),
            "values": vector.values.tolist()
        }

    async def search(self, collection_name: str, query: str, stroke_subtype: Optional[str] = None, top_k: int = 5) -> \
            List[Dict[str, Any]]:
        try:
            # 1. Получаем HYDE вектор, raw вектор и sparse параллельно
            messages = [{"role": "system", "content": HYDE_PROMPT.format(query=query)}]
            hyde_text = await self.llm_handler.chat_completion(messages, temperature=0.0)

            # 2. Получаем оба вектора одним батчем (1 запрос Embedding)
            vectors = await self.llm_handler.get_embeddings_batch([hyde_text, query])
            dense_vector, raw_vector = vectors[0], vectors[1]

            # 3. Sparse делается локально
            sparse_vector = await self.get_sparse_embedding(query)

            # 2. Настройка фильтра
            search_filter = None
            if stroke_subtype:
                search_filter = models.Filter(
                    must=[models.FieldCondition(key="subtype", match=models.MatchValue(value=stroke_subtype))]
                )

            # 3. Гибридный поиск с RRF для ранжирования
            results = await self.qdrant_client.query_points(
                collection_name=collection_name,
                prefetch=[
                    models.Prefetch(
                        query=dense_vector,
                        using="dense",
                        limit=top_k,
                    ),
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=sparse_vector["indices"],
                            values=sparse_vector["values"]
                        ),
                        using="sparse",
                        filter=search_filter,
                        limit=top_k,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=top_k,
                with_payload=True,
            )

            # 4. Фоллбек если гибридный поиск не дал результатов
            if not results.points:
                logger.info("Hybrid search returned no results, retrying with direct embedding...")
                results = await self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=raw_vector,
                    using="dense",
                    query_filter=search_filter,
                    limit=top_k,
                    with_payload=True,
                )

            if not results.points:
                return []

            # 5. Получаем косинусный score топового чанка по HYDE и по raw запросу параллельно
            top_id = results.points[0].id
            id_filter = models.Filter(must=[models.HasIdCondition(has_id=[top_id])])

            hyde_check, raw_check = await asyncio.gather(
                self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=dense_vector,
                    using="dense",
                    query_filter=id_filter,
                    limit=1,
                    with_payload=False,
                ),
                self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=raw_vector,
                    using="dense",
                    query_filter=id_filter,
                    limit=1,
                    with_payload=False,
                )
            )

            hyde_cosine = hyde_check.points[0].score if hyde_check.points else 0.0
            raw_cosine = raw_check.points[0].score if raw_check.points else 0.0
            avg_confidence = (hyde_cosine + raw_cosine) / 2

            # 6. Логирование
            logger.info(
                f"TOP CHUNK | id={top_id} | "
                f"hyde_cosine={hyde_cosine:.4f} | raw_cosine={raw_cosine:.4f} | avg_confidence={avg_confidence:.4f}"
            )
            for i, point in enumerate(results.points):
                parent_content = point.payload.get("parent_content", point.payload.get("content", ""))
                logger.info(
                    f"Chunk [{i + 1}/{len(results.points)}] | "
                    f"id={point.id} | "
                    f"rrf_score={point.score:.4f} | "
                    f"parent_content={parent_content[:200]}..."
                )

            # 7. Возвращаем: для топового score = среднее HYDE и raw косинусов
            return [
                {
                    "id": point.id,
                    "score": avg_confidence if i == 0 else point.score,
                    "content": point.payload.get("parent_content", point.payload.get("content", "")),
                    "source": point.payload.get("metadata", {}).get("source", "")
                } for i, point in enumerate(results.points)
            ]

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []

    def create_collection_if_not_exists(self, name: str, sync_client: QdrantClient):
        if not sync_client.collection_exists(collection_name=name):
            sync_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=settings.EMBEDDING_SIZE, distance=Distance.COSINE)
            )

    def ingest_documents(self, collection_name: str, documents: List[Dict[str, Any]], sync_client: QdrantClient):
        self.create_collection_if_not_exists(collection_name, sync_client)
        points = []
        for doc in documents:
            points.append(PointStruct(
                id=uuid.uuid4().hex,
                vector=doc["vector"],
                payload={
                    "content": doc["content"],
                    "source": doc.get("source", ""),
                    "subtype": doc.get("subtype", "general")
                }
            ))
        sync_client.upsert(collection_name=collection_name, points=points)