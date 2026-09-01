import logging
from typing import Dict, Any, List

from langgraph.config import get_stream_writer

from app.schemas import GraphState, ResponseType

logger = logging.getLogger(__name__)


async def off_topic_node(state: GraphState) -> Dict[str, Any]:
    write = get_stream_writer()
    response_text = (
        "Я здесь, чтобы помочь вам с вопросами по инсульту, реабилитации и самочувствию. "
        "Спросите меня о лекарствах, давлении или как получить поддержку."
    )
    write({"type": "token", "content": response_text})
    history: List[Dict[str, str]] = list(state.get("messages") or [])
    return {
        "response_text": response_text,
        "response_type": ResponseType.text,
        "messages": history + [{"role": "assistant", "content": response_text}],
        "backend_commands": [],
    }