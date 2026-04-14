import uuid
import logging
from typing import List, Optional, Dict, Any
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.config import settings
from app.llm import LLMHandler

logger = logging.getLogger(__name__)

HYDE_PROMPT = """Ты — невролог, пишешь фрагмент клинических рекомендаций.
Напиши 3-4 предложения медицинским языком которые отвечают на вопрос пациента, перенесшего инсульт. 
Используй медицинскую терминологию и аббревиатуры характерные для российских клинических рекомендаций.
Только текст фрагмента, без вступлений и пояснений.

Вопрос: {query}"""


class RAGService:
    def __init__(self, qdrant_client: AsyncQdrantClient, llm_handler: LLMHandler):
        self.qdrant_client = qdrant_client
        self.llm_handler = llm_handler

    async def _get_hyde_vector(self, query: str) -> List[float]:
        try:
            messages = [{"role": "system", "content": HYDE_PROMPT.format(query=query)}]
            hypothetical_doc = await self.llm_handler.chat_completion(messages)
            logger.info(f"HyDE generated doc: {hypothetical_doc[:100]}...")
            return await self.llm_handler.get_embedding(hypothetical_doc)
        except Exception as e:
            logger.warning(f"HyDE failed, falling back to direct embedding: {e}")
            return await self.llm_handler.get_embedding(query)

    async def search(self, collection_name: str, query: str, stroke_subtype: Optional[str] = None, top_k: int = 5) -> \
            List[Dict[str, Any]]:

        try:
            query_vector = await self._get_hyde_vector(query)

            search_filter = None
            if stroke_subtype:
                search_filter = Filter(must=[FieldCondition(key="subtype", match=MatchValue(value=stroke_subtype))])

            results = await self.qdrant_client.query_points(
                collection_name=collection_name,
                query=query_vector,
                using="dense",
               # query_filter=search_filter,
                limit=top_k,
                with_payload=False,
            )

            logger.info(f"RAG query returned {len(results.points)} points, "
                        f"scores: {[round(p.score, 3) for p in results.points]}")

            # Если HyDE не дал хороших результатов — повторить с прямым embedding
            if not results.points or results.points[0].score < 0.3:
                logger.info("HyDE scores low, retrying with direct query embedding...")
                direct_vector = await self.llm_handler.get_embedding(query)
                results = await self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=direct_vector,
                    using="dense",
                    query_filter=search_filter,
                    limit=top_k,
                    with_payload=False,
                    score_threshold=0.0
                )
                logger.info(f"Direct query scores: {[round(p.score, 3) for p in results.points]}")

            if not results.points:
                return []

            ids = [point.id for point in results.points]
            scores = {point.id: point.score for point in results.points}

            points_with_payload = await self.qdrant_client.retrieve(
                collection_name=collection_name,
                ids=ids,
                with_payload=True,
                with_vectors=False
            )

            logger.info(f"RAG retrieve returned {len(points_with_payload)} points")

            return [
                {"id": str(p.id), "content": p.payload.get("content", ""), "score": scores[p.id],
                 "metadata": p.payload}
                for p in points_with_payload
            ]

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise

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