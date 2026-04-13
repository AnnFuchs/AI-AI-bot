import os
import sys
import uuid
import logging
import argparse
from typing import List, Dict, Any
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, UnstructuredPDFLoader
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)
qdrant_client = QdrantClient(url=settings.QDRANT_URL)

def load_documents(folder_path: str) -> List[Dict[str, Any]]:
    """Load documents from a folder and split them into chunks."""
    docs = []
    p = Path(folder_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    
    for file in p.rglob('*'):
        if file.suffix in ['.txt', '.md']:
            loader = TextLoader(str(file), encoding='utf-8')
            raw_docs = loader.load()
            split = splitter.split_documents(raw_docs)
            for d in split:
                docs.append({
                    "content": d.page_content,
                    "metadata": {"source": str(file), "type": file.suffix}
                })
        elif file.suffix == '.pdf':
            loader = UnstructuredPDFLoader(str(file))
            raw_docs = loader.load()
            split = splitter.split_documents(raw_docs)
            for d in split:
                docs.append({
                    "content": d.page_content,
                    "metadata": {"source": str(file), "type": file.suffix}
                })
    return docs

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings for a list of texts."""
    resp = await openai_client.embeddings.create(input=texts, model=settings.OPENAI_EMBEDDING_MODEL)
    return [d.embedding for d in resp.data]

def upload_to_qdrant(collection_name: str, points: List[PointStruct]):
    """Upload points to Qdrant."""
    if not qdrant_client.collection_exists(collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
    qdrant_client.upsert(collection_name=collection_name, points=points)

async def main(folder: str, collection: str):
    logger.info(f"Loading documents from {folder}...")
    docs = load_documents(folder)
    if not docs:
        logger.warning("No documents found.")
        return

    contents = [d['content'] for d in docs]
    
    # Embedding in batches if needed, here assuming manageable size for hackathon
    embeddings = await get_embeddings(contents)
    
    points = []
    for i, doc in enumerate(docs):
        points.append(PointStruct(
            id=uuid.uuid4().hex,
            vector=embeddings[i],
            payload={
                "content": doc['content'],
                "source": doc['metadata']['source']
            }
        ))
        
    logger.info(f"Uploading {len(points)} chunks to Qdrant...")
    upload_to_qdrant(collection, points)
    logger.info("Ingestion completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant")
    parser.add_argument("--folder", required=True, help="Path to documents folder")
    parser.add_argument("--collection", required=True, help="Qdrant collection name")
    args = parser.parse_args()
    
    import asyncio
    asyncio.run(main(args.folder, args.collection))
