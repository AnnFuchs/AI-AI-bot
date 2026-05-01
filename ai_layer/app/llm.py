import logging
import asyncio
from typing import AsyncGenerator, Type, TypeVar

from pydantic import BaseModel
from langchain_gigachat import GigaChat
from langchain_gigachat.embeddings import GigaChatEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from gigachat.exceptions import GigaChatException, RateLimitError, AuthenticationError

from app.config import settings

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)

# Типы ролей которые приходят из графа
_ROLE_MAP = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


def _to_lc_messages(messages: list[dict]) -> list[BaseMessage]:
    """Конвертирует список dict-сообщений в LangChain BaseMessage."""
    result = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        cls = _ROLE_MAP.get(role)
        if cls is None:
            logger.warning(f"Неизвестная роль сообщения: {role!r}, пропускаем")
            continue
        result.append(cls(content=content))
    return result


class LLMHandler:
    """
    Обёртка над GigaChat через langchain-gigachat.

    Два клиента с разными таймаутами:
    - _fast_llm: classifier, reminder, data_input (30s)
    - _slow_llm: education stream, wellbeing stream, clarification (120s)

    Retry, connection pool — делегированы SDK.
    Embeddings — через GigaChatEmbeddings (нативный async).
    """

    def __init__(self) -> None:
        _common = dict(
            credentials=settings.GIGACHAT_CREDENTIALS,
            scope=settings.GIGACHAT_SCOPE,
            model=settings.GIGACHAT_MODEL,
            verify_ssl_certs=False,
            max_retries=settings.LLM_MAX_RETRIES,
            retry_backoff_factor=settings.LLM_RETRY_BACKOFF_FACTOR,
        )
        self._fast_llm = GigaChat(
            **_common,
            timeout=settings.LLM_TIMEOUT_FAST,
        )
        self._slow_llm = GigaChat(
            **_common,
            timeout=settings.LLM_TIMEOUT_SLOW,
        )
        self._embeddings = GigaChatEmbeddings(
            credentials=settings.GIGACHAT_CREDENTIALS,
            scope=settings.GIGACHAT_SCOPE,
            model=settings.GIGACHAT_EMBEDDING_MODEL,
            verify_ssl_certs=False,
        )

    async def close(self) -> None:
        """Закрыть HTTP-соединения обоих клиентов."""
        # langchain-gigachat клиент не требует явного закрытия,
        # но если появится — здесь правильное место
        pass

    # ── Основные методы ───────────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
        use_slow_client: bool = False,
    ) -> str:
        """
        Неструктурированный текстовый ответ.
        Используй для: wellbeing, emotional, education, clarification response.
        """
        llm = self._slow_llm if use_slow_client else self._fast_llm
        lc_messages = _to_lc_messages(messages)
        try:
            result = await llm.ainvoke(lc_messages, temperature=temperature)
            return result.content or ""
        except RateLimitError as e:
            logger.warning(f"Rate limit. Retry after {e.retry_after}s")
            raise
        except AuthenticationError:
            logger.error("GigaChat auth failed — проверь GIGACHAT_CREDENTIALS")
            raise
        except GigaChatException as e:
            logger.error(f"GigaChat error: {e}")
            raise

    async def complete_structured(self, messages, response_model, *, temperature=0.2, method=None):
        logger.info(f"complete_structured: model={self._fast_llm.model}, schema={response_model.__name__}")
        if method:
            llm = self._fast_llm.bind(temperature=temperature).with_structured_output(response_model, method=method)
        else:
            llm = self._fast_llm.bind(temperature=temperature).with_structured_output(response_model)
        lc_messages = _to_lc_messages(messages)
        logger.info(f"complete_structured: calling ainvoke, messages count={len(lc_messages)}")
        try:
            result = await llm.ainvoke(lc_messages)
            logger.info(f"complete_structured: ainvoke returned: {result}")
            return result
        except RateLimitError as e:
            logger.warning(f"Rate limit. Retry after {e.retry_after}s")
            raise
        except GigaChatException as e:
            logger.error(f"GigaChat structured error: {e}")
            raise

    async def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.5,
    ) -> AsyncGenerator[str, None]:
        """
        Стриминг токенов.
        Используй для: wellbeing, education, emotional — всё что идёт напрямую в SSE.
        """
        lc_messages = _to_lc_messages(messages)
        try:
            async for chunk in self._slow_llm.astream(lc_messages, temperature=temperature):
                content = chunk.content
                if content:
                    yield content
        except RateLimitError as e:
            logger.warning(f"Stream rate limit. Retry after {e.retry_after}s")
            yield ""
        except GigaChatException as e:
            logger.error(f"Stream error: {e}")
            yield ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Получить эмбеддинги батчем.
        Используй в RAGService.search().
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                self._embeddings.embed_documents,
                texts,
            )
        except GigaChatException as e:
            logger.error(f"Embedding error: {e}")
            raise

    async def count_tokens(self, messages: list[dict]) -> int:
        """
        Подсчёт токенов до отправки запроса.
        Используй перед передачей истории в LLM для trimming.

        Returns:
            Количество токенов или 0 при ошибке.
        """
        lc_messages = _to_lc_messages(messages)
        # GigaChatEmbeddings не имеет count_tokens —
        # используем приближение: 1 токен ≈ 4 символа (для русского ближе к 3)
        # TODO: заменить на реальный API когда SDK добавит async tokens_count
        total_chars = sum(len(m.content) for m in lc_messages)
        return total_chars // 3