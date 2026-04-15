import uuid
import logging
import argparse
import asyncio
import pdfplumber
from typing import List, Dict, Any
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_gigachat.embeddings import GigaChatEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SparseVectorParams
from fastembed import SparseTextEmbedding

from ai_layer.app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

qdrant_client = QdrantClient(url=settings.QDRANT_URL)
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

gigachat_embeddings = GigaChatEmbeddings(
    credentials=settings.GIGACHAT_CREDENTIALS,
    scope=settings.GIGACHAT_SCOPE,
    model='EmbeddingsGigaR',
    verify_ssl_certs=False,
)


def extract_text_with_pdfplumber(file_path: str) -> str:
    full_text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=True, use_text_flow=True)
            if page_text:
                full_text.append(page_text)
    return "\n".join(full_text)


def load_documents(folder_path: str) -> List[Dict[str, Any]]:
    """
    Иерархический чанкинг:
    - Родитель: 1800 символов, overlap 300 — передаётся LLM как контекст
    - Ребёнок: 400 символов, overlap 80 — используется для векторного поиска
    Каждый дочерний чанк хранит parent_content в payload.
    """
    docs = []
    p = Path(folder_path)

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800,
        chunk_overlap=300,
    )

    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
    )

    for file in p.rglob('*'):
        try:
            if file.suffix in ['.txt', '.md']:
                from langchain_community.document_loaders import TextLoader
                loader = TextLoader(str(file), encoding='utf-8')
                raw_docs = loader.load()
                parent_docs = parent_splitter.split_documents(raw_docs)
                texts = [d.page_content for d in parent_docs]
            elif file.suffix == '.pdf':
                logger.info(f"Processing PDF: {file.name}")
                text = extract_text_with_pdfplumber(str(file))
                texts = [d.page_content for d in parent_splitter.create_documents([text])]
            else:
                continue

            logger.info(f"Hierarchical chunking: {file.name} ({len(texts)} parent chunks)...")

            child_idx = 0
            for parent_idx, parent_text in enumerate(texts):
                children = child_splitter.create_documents([parent_text])
                for child in children:
                    docs.append({
                        "content": child.page_content,        # индексируется в Qdrant
                        "parent_content": parent_text,        # отдаётся LLM
                        "metadata": {
                            "source": str(file.name),
                            "parent_idx": parent_idx,
                            "chunk_idx": child_idx,
                            "type": file.suffix,
                        }
                    })
                    child_idx += 1

        except Exception as e:
            logger.error(f"Failed to load {file.name}: {e}")

    logger.info(f"Total child chunks: {len(docs)}")
    return docs


async def get_dense_embeddings(texts: List[str]) -> List[List[float]]:
    loop = asyncio.get_event_loop()
    all_embeddings = []
    batch_size = 20

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        logger.info(f"Dense embeddings: batch {i // batch_size + 1} / {(len(texts) - 1) // batch_size + 1}")
        embeddings = await loop.run_in_executor(
            None, gigachat_embeddings.embed_documents, batch
        )
        all_embeddings.extend(embeddings)

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

    # Эмбеддим дочерние чанки (маленькие, точные)
    contents = [d['content'] for d in docs]

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
                "content": doc['content'],           # маленький чанк (для отладки)
                "parent_content": doc['parent_content'],  # большой чанк (для LLM)
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