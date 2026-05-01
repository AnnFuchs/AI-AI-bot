import logging
from typing import Dict, Any, List

from langgraph.config import get_stream_writer

from app.schemas import (
    GraphState, IntentEnum, ResponseType,
    SourceReference, ResponseMeta, Button,
)
from app.prompts import EDUCATION_SYSTEM_PROMPT
from app.llm import LLMHandler
from app.rag import RAGService
from app.graph.helpers import _get_user_context, _build_patient_context_str, _build_confidence_label

logger = logging.getLogger(__name__)


async def education_node(state: GraphState, llm_handler: LLMHandler, rag_service: RAGService) -> Dict[str, Any]:
    write = get_stream_writer()
    user_ctx = _get_user_context(state)
    subtype = user_ctx.stroke_toast_subtype if user_ctx else None
    collections = ["stroke_clinrecs_gigaembed"]
    docs = []
    scores = []

    for coll in collections:
        res = await rag_service.search(coll, state["user_message"], stroke_subtype=subtype)
        docs.extend(res)
        scores.extend([d["score"] for d in res])

    rag_conf = max(scores) if scores else 0.0
    confidence_label = _build_confidence_label(rag_conf)
    sources = [
        SourceReference(source=d.get("source", ""))
        for d in docs[:5] if d.get("source")
    ]
    intent = state.get("intent", IntentEnum.education)
    history: List[Dict[str, str]] = list(state.get("messages") or [])

    if confidence_label == "insufficient":
        fallback_text = (
            "В доступных клинических рекомендациях нет точного ответа на этот вопрос. "
            "Пожалуйста, уточните у вашего лечащего врача."
        )
        meta = ResponseMeta(
            confidence=rag_conf, confidence_label=confidence_label,
            sources=[], intent=str(intent), used_rag=True,
        )
        write({"type": "buttons", "payload": [Button(label="Общая памятка", href="/learn").model_dump()]})
        write({"type": "token", "content": fallback_text})
        write({"type": "sources", "payload": meta.model_dump()})

        current_user_message = state["user_message"]
        sanitized_history = []
        replaced = False
        for msg in reversed(history):
            if not replaced and msg.get("role") == "user" and msg.get("content") == current_user_message:
                sanitized_history.insert(0, {"role": "user", "content": "[вопрос вне базы знаний]"})
                replaced = True
            else:
                sanitized_history.insert(0, msg)
        sanitized_history.append({"role": "assistant", "content": fallback_text})

        return {
            "response_text": fallback_text,
            "response_type": ResponseType.text_with_buttons,
            "buttons": [Button(label="Общая памятка", href="/learn")],
            "backend_commands": [],
            "response_meta": meta,
            "messages": sanitized_history,
        }

    context = "\n\n".join([d["content"] for d in docs[:5]])
    patient_ctx = _build_patient_context_str(user_ctx)
    sys_prompt = f"{EDUCATION_SYSTEM_PROMPT}\nКонтекст: {context}{patient_ctx}"
    chat_messages = [{"role": "system", "content": sys_prompt}] + history

    full_text = ""
    try:
        async for token in llm_handler.stream(chat_messages):
            full_text += token
            write({"type": "token", "content": token})
    except Exception as e:
        logger.error(f"Education stream error: {e}")
        full_text = "Произошла ошибка при генерации ответа."

    meta = ResponseMeta(
        confidence=rag_conf, confidence_label=confidence_label,
        sources=sources, intent=str(intent), used_rag=True,
    )
    write({"type": "sources", "payload": meta.model_dump()})

    return {
        "response_text": full_text,
        "response_type": ResponseType.text,
        "messages": history + [{"role": "assistant", "content": full_text}],
        "backend_commands": [],
        "response_meta": meta,
    }