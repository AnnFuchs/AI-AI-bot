import json
import logging
from typing import Any, AsyncGenerator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.commands import get_sources, handle_backend_commands
from src.core.config import settings
from src.users.models import User

logger = logging.getLogger(__name__)


async def build_event_stream(
    ai_payload: dict[str, Any],
    user: User,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Create event stream for chat endpoint."""
    user_id = ai_payload.get('user_id')
    session_id = ai_payload.get('session_id')
    events_yielded = 0

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                'POST',
                f'{settings.AI_LAYER_URL}/chat/stream',
                json=ai_payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith('data:'):
                        continue

                    raw = line[5:].strip()
                    if not raw:
                        continue

                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning(
                            'Bad SSE line | user_id=%s session_id=%s line=%r',
                            user_id, session_id, raw,
                        )
                        continue

                    event_type = event.get('type')

                    if event_type == 'commands':
                        await handle_backend_commands(
                            event.get('payload', []), user, db,
                        )
                        continue

                    if event_type == 'sources':
                        sources = await get_sources(
                            event.get('payload', {}), db,
                        )
                        events_yielded += 1
                        yield (
                            f'data: {
                                json.dumps(
                                    {
                                        'type': 'sources',
                                        'payload': sources
                                    }, ensure_ascii=False
                                )
                            }\n\n'
                        )
                        continue

                    events_yielded += 1
                    yield (
                        f'data: {
                            json.dumps(event, ensure_ascii=False)
                        }\n\n'
                    )
        logger.info(
            'Chat stream completed | user_id=%s session_id=%s events=%d',
            user_id, session_id, events_yielded,
        )

    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:200]
        logger.error(
            (
                'AI layer returned error',
                'user_id=%s session_id=%s status=%s body=%r',
            ),
            user_id, session_id, exc.response.status_code, body,
        )
        yield (
            f"data: {
                json.dumps(
                    {'type': 'error', 'message': 'AI service unavailable'})
                }\n\n"
        )
    except httpx.RequestError:
        logger.exception(
            'AI layer unreachable | user_id=%s session_id=%s',
            user_id, session_id,
        )
        yield (
            f"data: {
                json.dumps(
                    {'type': 'error', 'message': 'AI service unavailable'})
                }\n\n"
        )
    except Exception:
        logger.exception(
            'Unexpected error in event stream | user_id=%s session_id=%s',
            user_id, session_id,
        )
        yield (
            f"data: {
                json.dumps(
                    {'type': 'error', 'message': 'Internal server error'})
                }\n\n"
        )
