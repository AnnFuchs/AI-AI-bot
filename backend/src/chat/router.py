import json
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.chat.commands import get_sources, handle_backend_commands
from src.chat.context import build_user_context
from src.chat.schemas import ChatRequest
from src.core.config import settings
from src.core.logger import logger
from src.db.session import get_async_session
from src.users.models import User

router = APIRouter(prefix='/chat', tags=['Chat'])


@router.post('/stream')
async def chat_stream(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Create main chat endpoint."""
    user_context = await build_user_context(user, db)

    ai_payload = {
        'user_id': str(user.id),
        'session_id': str(request.session_id),
        'message': request.message,
        'user_context': user_context.model_dump(mode="json"),
    }

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    'POST',
                    f'{settings.AI_LAYER_URL}/chat/stream',
                    json=ai_payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if not line.startswith('data:'):
                            continue

                        raw = line[5:].strip()
                        if not raw:
                            continue

                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warning('Bad SSE line: %s', raw)
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

                        yield (
                            f'data: {
                                json.dumps(event, ensure_ascii=False)
                            }\n\n'
                        )

        except httpx.RequestError:
            logger.exception('AI layer unreachable')
            yield (
                f"data: {
                    json.dumps(
                        {'type': 'error', 'message': 'AI service unavailable'})
                    }\n\n"
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
