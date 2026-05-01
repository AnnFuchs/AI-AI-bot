import uuid
import logging
from typing import List, Optional, Dict, Any
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import settings
from app.llm import LLMHandler
import asyncio
from qdrant_client.http import models

logger = logging.getLogger(__name__)

HYDE_PROMPT = """Ты — невролог, пишешь фрагмент клинических рекомендаций для пациента после инсульта.
Напиши 3-4 предложения медицинским языком которые отвечают на вопрос пациента, перенесшего инсульт.
Используй медицинскую терминологию и аббревиатуры характерные для российских клинических рекомендаций.
Помни: ОНМК, инфаркт мозга, ишемический инсульт — это связанные понятия в контексте инсульта.
Только текст фрагмента, без вступлений и пояснений.

Вопрос: {query}"""

COSINE_SCORE_THRESHOLD = 0.3


class RAGService:
    def __init__(self, qdrant_client: AsyncQdrantClient, llm_handler: LLMHandler):
        self.qdrant_client = qdrant_client
        self.llm_handler = llm_handler

    async def search(self, collection_name: str, query: str, stroke_subtype: Optional[str] = None, top_k: int = 5) -> \
            List[Dict[str, Any]]:
        try:
            # 1. Генерируем HyDE текст
            messages = [{"role": "system", "content": HYDE_PROMPT.format(query=query)}]
            hyde_text = await self.llm_handler.complete(messages, temperature=0.0)
            logger.info(f"HyDE generated doc: {hyde_text}...")

            # 2. Получаем dense векторы батчем (1 запрос к Embedding API)
            vectors = await self.llm_handler.embed([hyde_text, query])
            dense_vector, raw_vector = vectors[0], vectors[1]

            # 3. Настройка фильтра
            search_filter = None
            if stroke_subtype:
                search_filter = models.Filter(
                    must=[models.FieldCondition(key="subtype", match=models.MatchValue(value=stroke_subtype))]
                )

            # 4. Поиск по HyDE вектору
            results = await self.qdrant_client.query_points(
                collection_name=collection_name,
                query=dense_vector,
                using="dense",
                query_filter=search_filter,
                limit=top_k,
                with_payload=True,
            )

            if not results.points:
                logger.info("HyDE search returned no results, retrying with raw query embedding...")
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

            # 5. Получаем raw cosine scores для всех чанков параллельно
            all_ids = [p.id for p in results.points]
            ids_filter = models.Filter(must=[models.HasIdCondition(has_id=all_ids)])

            hyde_check, raw_check = await asyncio.gather(
                self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=dense_vector,
                    using="dense",
                    query_filter=ids_filter,
                    limit=len(all_ids),
                    with_payload=False,
                ),
                self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=raw_vector,
                    using="dense",
                    query_filter=ids_filter,
                    limit=len(all_ids),
                    with_payload=False,
                )
            )

            hyde_scores = {p.id: p.score for p in hyde_check.points}
            raw_scores = {p.id: p.score for p in raw_check.points}

            def avg_cosine(point_id):
                return (hyde_scores.get(point_id, 0.0) + raw_scores.get(point_id, 0.0)) / 2

            # 6. Сортируем по avg cosine и фильтруем по порогу
            results.points.sort(key=lambda p: avg_cosine(p.id), reverse=True)

            filtered_points = [p for p in results.points if avg_cosine(p.id) >= COSINE_SCORE_THRESHOLD]

            if not filtered_points:
                best = avg_cosine(results.points[0].id)
                logger.info(f"All chunks below threshold={COSINE_SCORE_THRESHOLD}, best avg_cosine={best:.4f}")
                return []

            # 7. Логирование
            top_id = filtered_points[0].id
            logger.info(
                f"TOP CHUNK | id={top_id} | "
                f"hyde_cosine={hyde_scores.get(top_id, 0.0):.4f} | "
                f"raw_cosine={raw_scores.get(top_id, 0.0):.4f} | "
                f"avg_confidence={avg_cosine(top_id):.4f}"
            )
            for i, point in enumerate(filtered_points):
                parent_content = point.payload.get("parent_content", point.payload.get("content", ""))
                logger.info(
                    f"Chunk [{i + 1}/{len(filtered_points)}] | "
                    f"id={point.id} | "
                    f"avg_cosine={avg_cosine(point.id):.4f} | "
                    f"parent_content={parent_content[:200]}..."
                )

            # 8. Возвращаем с детерминированным avg_cosine score
            return [
                {
                    "id": point.id,
                    "score": avg_cosine(point.id),
                    "content": point.payload.get("parent_content", point.payload.get("content", "")),
                    "source": point.payload.get("source", point.payload.get("metadata", {}).get("source", ""))
                } for point in filtered_points
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