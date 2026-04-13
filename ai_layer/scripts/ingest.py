import os
import uuid
import logging
import argparse
import asyncio
import pdfplumber
from typing import List, Dict, Any
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SparseVectorParams
from fastembed import SparseTextEmbedding

from ai_layer.app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация клиентов
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)
qdrant_client = QdrantClient(url=settings.QDRANT_URL)
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


def extract_text_with_pdfplumber(file_path: str) -> str:
    """Извлечение текста с сохранением структуры таблиц через pdfplumber."""
    full_text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # Извлекаем текст. layout=True пытается сохранить визуальное расположение
            page_text = page.extract_text(layout=True, use_text_flow=True)
            if page_text:
                full_text.append(page_text)
    return "\n".join(full_text)


def load_documents(folder_path: str) -> List[Dict[str, Any]]:
    docs = []
    p = Path(folder_path)
    # Уменьшаем чанк до 600 для более точного попадания в медицинские термины
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)

    for file in p.rglob('*'):
        try:
            if file.suffix in ['.txt', '.md']:
                from langchain_community.document_loaders import TextLoader
                loader = TextLoader(str(file), encoding='utf-8')
                raw_docs = loader.load()
                split = splitter.split_documents(raw_docs)
            elif file.suffix == '.pdf':
                logger.info(f"Processing PDF with pdfplumber: {file.name}")
                text = extract_text_with_pdfplumber(str(file))
                # Создаем документы вручную, так как pdfplumber не возвращает объекты langchain
                split = splitter.create_documents([text])
            else:
                continue

            # Добавляем chunk_idx для каждого куска в рамках одного файла
            for i, d in enumerate(split):
                docs.append({
                    "content": d.page_content,
                    "metadata": {
                        "source": str(file.name),
                        "chunk_idx": i,
                        "type": file.suffix
                    }
                })
        except Exception as e:
            logger.error(f"Failed to load {file.name}: {e}")
    return docs


async def get_dense_embeddings(texts: List[str]) -> List[List[float]]:
    all_embeddings = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        logger.info(f"Dense embeddings: batch {i // batch_size + 1}")
        resp = await openai_client.embeddings.create(
            input=batch,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        all_embeddings.extend([d.embedding for d in resp.data])
    return all_embeddings


def upload_to_qdrant(collection_name: str, points: List[PointStruct], vector_size: int):
    if qdrant_client.collection_exists(collection_name):
        logger.info(f"Deleting collection {collection_name}")
        qdrant_client.delete_collection(collection_name)

    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": VectorParams(size=vector_size, distance=Distance.COSINE)
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams()
        }
    )

    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        qdrant_client.upsert(collection_name=collection_name, points=batch)
        logger.info(f"Qdrant: uploaded batch {i // batch_size + 1}")


async def main(folder: str, collection: str):
    logger.info(f"Loading documents from {folder}...")
    docs = load_documents(folder)
    if not docs:
        logger.warning("No documents found.")
        return

    contents = [d['content'] for d in docs]

    # Генерация векторов
    dense_embeddings = await get_dense_embeddings(contents)
    logger.info("Generating sparse embeddings (BM25)...")
    sparse_embeddings = list(sparse_model.embed(contents))

    points = []
    for i, doc in enumerate(docs):
        points.append(PointStruct(
            id=uuid.uuid4().hex,
            vector={
                "dense": dense_embeddings[i],
                "sparse": sparse_embeddings[i].as_object()
            },
            payload={
                "content": doc['content'],
                "metadata": doc['metadata']
            }
        ))

    logger.info(f"Uploading {len(points)} points to Qdrant...")
    upload_to_qdrant(collection, points, len(dense_embeddings[0]))
    logger.info("Ingestion completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--collection", required=True)
    args = parser.parse_args()

    asyncio.run(main(args.folder, args.collection))