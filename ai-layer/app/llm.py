import logging
from typing import Dict, List, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

class LLMHandler:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)

    async def close(self):
        if hasattr(self.client, "close"):
            await self.client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat_completion(self, messages: List[Dict[str, str]], response_format: Optional[Dict] = None) -> str:
        kwargs = {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "timeout": 30
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    async def chat_completion_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        try:
            resp = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                stream=True,
                timeout=30
            )
            async for chunk in resp:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming Chat Error: {e}")
            yield "Произошла ошибка при генерации ответа."

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            input=text,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        return response.data[0].embedding