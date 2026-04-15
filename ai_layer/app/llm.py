import logging
import base64
import asyncio
from typing import Dict, List, AsyncGenerator, Optional
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from langchain_gigachat.embeddings import GigaChatEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)


class LLMHandler:
    def __init__(self):

        self.client = GigaChat(
            credentials=settings.GIGACHAT_CREDENTIALS,
            verify_ssl_certs=False,
        )
        self.gigachat_embeddings = GigaChatEmbeddings(
            credentials=settings.GIGACHAT_CREDENTIALS,
            scope=settings.GIGACHAT_SCOPE,
            model='EmbeddingsGigaR',
            verify_ssl_certs=False,
        )

    async def close(self):
        await self.client.aclose()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
    ) -> str:
        payload = Chat(
            model=settings.OPENAI_MODEL,
            messages=[
                Messages(
                    role=MessagesRole(m["role"]),
                    content=m["content"],
                )
                for m in messages
            ],
        )
        for attempt in range(3):
            try:
                resp = await self.client.achat(payload)
                return resp.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"chat_completion attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise
                import asyncio
                await asyncio.sleep(2 ** attempt)
        return ""

    async def chat_completion_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        payload = Chat(
            model=settings.OPENAI_MODEL,
            messages=[
                Messages(
                    role=MessagesRole(m["role"]),
                    content=m["content"],
                )
                for m in messages
            ],
            stream=True,
        )
        try:
            async for chunk in self.client.astream(payload):
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Streaming Chat Error: {e}")
            yield "Произошла ошибка при генерации ответа."

    async def get_embedding(self, text: str) -> List[float]:
        loop = asyncio.get_event_loop()

        for attempt in range(3):
            try:
                embeddings = await loop.run_in_executor(
                    None, self.gigachat_embeddings.embed_documents, [text]
                )
                return embeddings[0]
            except Exception as e:
                logger.warning(f"get_embedding attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

        return []