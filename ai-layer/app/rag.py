import uuid
from typing import List, Optional, Dict, Any
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.config import settings
from app.llm import LLMHandler


class RAGService:
    def __init__(self, qdrant_client: AsyncQdrantClient, llm_handler: LLMHandler):
        self.qdrant_client = qdrant_client
        self.llm_handler = llm_handler

    async def search(self, collection_name: str, query: str, stroke_subtype: Optional[str] = None, top_k: int = 5) -> \
    List[Dict[str, Any]]:
        query_vector = await self.llm_handler.get_embedding(query)
        search_filter = None
        if stroke_subtype:
            search_filter = Filter(must=[FieldCondition(key="subtype", match=MatchValue(value=stroke_subtype))])

        results = await self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=top_k,
            with_payload=True
        )

        return [
            {"id": str(point.id), "content": point.payload.get("content", ""), "score": point.score,
             "metadata": point.payload}
            for point in results
        ]

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