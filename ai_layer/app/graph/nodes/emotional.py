import logging
from typing import Dict, Any, List

from langgraph.config import get_stream_writer

from app.schemas import GraphState, ResponseType
from app.prompts import EMOTIONAL_SYSTEM_PROMPT
from app.llm import LLMHandler
from app.graph.helpers import _get_user_context, _build_patient_context_str

logger = logging.getLogger(__name__)


async def emotional_node(state: GraphState, llm_handler: LLMHandler) -> Dict[str, Any]:
    write = get_stream_writer()
    patient_ctx = _build_patient_context_str(_get_user_context(state))
    history: List[Dict[str, str]] = list(state.get("messages") or [])
    chat_messages = [{"role": "system", "content": EMOTIONAL_SYSTEM_PROMPT + patient_ctx}] + history

    full_text = ""
    try:
        async for token in llm_handler.stream(chat_messages):
            full_text += token
            write({"type": "token", "content": token})
    except Exception as e:
        logger.error(f"Emotional stream error: {e}")
        full_text = "Я здесь, чтобы выслушать вас."
        write({"type": "token", "content": full_text})

    return {
        "response_text": full_text,
        "response_type": ResponseType.text,
        "messages": history + [{"role": "assistant", "content": full_text}],
        "backend_commands": [],
    }