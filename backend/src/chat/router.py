import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.chat.context import build_user_context
from src.chat.schemas import ChatRequest
from src.chat.stream import build_event_stream
from src.db.session import get_async_session
from src.users.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/chat', tags=['Chat'])


@router.post('/stream')
async def chat_stream(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Stream chat responses from the AI layer."""
    logger.info(
        'Chat stream request | user_id=%s session_id=%s',
        user.id,
        request.session_id,
    )
    user_context = await build_user_context(user, db)

    ai_payload = {
        'user_id': str(user.id),
        'session_id': str(request.session_id),
        'message': request.message,
        'user_context': user_context.model_dump(mode="json"),
    }

    return StreamingResponse(
        build_event_stream(ai_payload, user, db),
        media_type="text/event-stream",
    )
