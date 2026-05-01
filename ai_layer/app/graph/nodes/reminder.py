import logging
from typing import Dict, Any, List

from langgraph.config import get_stream_writer

from app.schemas import GraphState, ResponseType, BackendCommand, ReminderResponse
from app.prompts import REMINDER_SYSTEM_PROMPT
from app.llm import LLMHandler
from app.graph.helpers import _get_user_context, _build_patient_context_str

logger = logging.getLogger(__name__)


async def reminder_node(state: GraphState, llm_handler: LLMHandler) -> Dict[str, Any]:
    write = get_stream_writer()
    patient_ctx = _build_patient_context_str(_get_user_context(state))
    messages = [
        {"role": "system", "content": REMINDER_SYSTEM_PROMPT + patient_ctx},
        {"role": "user", "content": state["user_message"]},
    ]

    try:
        result = await llm_handler.complete_structured(messages, ReminderResponse)
        cmd = BackendCommand(
            command_type="UPSERT_REMINDER",
            payload=result.model_dump(),
        ).model_dump()
    except Exception as e:
        logger.error(f"Reminder extraction failed: {e}")
        cmd = None

    history: List[Dict[str, str]] = list(state.get("messages") or [])
    commands = [cmd] if cmd else []

    if commands:
        write({"type": "commands", "payload": commands})

    response_text = "Напоминание сохранено." if cmd else "Не удалось сохранить напоминание."
    write({"type": "token", "content": response_text})

    return {
        "response_text": response_text,
        "response_type": ResponseType.text,
        "messages": history + [{"role": "assistant", "content": response_text}],
        "backend_commands": commands,
    }