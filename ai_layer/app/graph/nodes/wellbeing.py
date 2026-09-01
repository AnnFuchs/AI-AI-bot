import logging
from typing import Dict, Any, List

from langgraph.config import get_stream_writer

from app.schemas import (
    GraphState, ResponseType, SymptomsData,
    RedFlagAlert, BackendCommand, WellbeingExtractionResponse,
)
from app.prompts import WELLBEING_EXTRACT_PROMPT, WELLBEING_SYSTEM_PROMPT
from app.llm import LLMHandler
from app.rules import evaluate_red_flags
from app.graph.helpers import (
    _get_user_context, _build_patient_context_str,
    _merge_symptoms, _enrich_symptoms_with_history,
    _assess_wellbeing_heuristic, _build_diary_commands,
    _has_stroke_symptoms,
    STROKE_SYMPTOM_KEYS,
)

logger = logging.getLogger(__name__)


async def wellbeing_node(state: GraphState, llm_handler: LLMHandler) -> Dict[str, Any]:
    write = get_stream_writer()
    user_message = state["user_message"]
    user_ctx = _get_user_context(state)
    patient_ctx = _build_patient_context_str(user_ctx)

    extract_messages = [
        {"role": "system", "content": WELLBEING_EXTRACT_PROMPT + patient_ctx},
        {"role": "user", "content": user_message},
    ]

    try:
        extracted = await llm_handler.complete_structured(
            extract_messages, WellbeingExtractionResponse
        )
        logger.info(f"Extracted raw: {extracted}")  # добавить эту строку
        symptoms = SymptomsData(
            symptoms={
                k: v for k, v in extracted.symptoms.model_dump().items()
                if v is not None
            },
            blood_pressure=extracted.blood_pressure,
            medications_taken=extracted.medications_taken,
        )
    except Exception as e:
        logger.error(f"Wellbeing extraction failed: {e}")
        symptoms = SymptomsData()

    symptoms.free_text = user_message
    symptoms.general_wellbeing = _assess_wellbeing_heuristic(symptoms)
    if user_ctx:
        symptoms.age_category = symptoms.age_category or user_ctx.age_category

    accumulated = state.get("accumulated_symptoms")
    if isinstance(accumulated, dict):
        try:
            accumulated = SymptomsData(**accumulated)
        except Exception as e:
            logger.error(f"accumulated_symptoms deserialization failed: {e}")
            accumulated = None

    merged_symptoms = _merge_symptoms(accumulated, symptoms)
    if user_ctx and user_ctx.known_symptoms is not None:
        merged_symptoms = _enrich_symptoms_with_history(merged_symptoms, user_ctx.known_symptoms)

    logger.info(
        f"Symptoms this turn: {list(symptoms.symptoms.keys())} | "
        f"Accumulated: {list(merged_symptoms.symptoms.keys())} | "
        f"is_new: { {k: v.is_new for k, v in merged_symptoms.symptoms.items()} }"
    )

    known_symptoms = (user_ctx.known_symptoms or []) if user_ctx else []
    stroke_date = user_ctx.stroke_date if user_ctx else None
    fast_checked = state.get("fast_checked", False)
    history: List[Dict[str, str]] = list(state.get("messages") or [])

    flags = evaluate_red_flags(
        merged_symptoms,
        known_symptoms=known_symptoms,
        stroke_date=stroke_date,
        fast_checked=fast_checked,
    )
    has_emergency = any(f.level == "emergency" for f in flags)
    has_urgent = any(f.level == "urgent" for f in flags)

    current_stroke_symptoms = {
        k for k, v in symptoms.symptoms.items()
        if k in STROKE_SYMPTOM_KEYS and v.present
    }
    already_triaged = set(state.get("triaged_symptoms") or [])
    new_stroke_symptoms = current_stroke_symptoms - already_triaged

    if _has_stroke_symptoms(merged_symptoms) and (not fast_checked or new_stroke_symptoms):
        logger.info("Stroke symptoms detected, fast_checked=False — deferring to clarification")
        diary_commands = _build_diary_commands(
            symptoms=symptoms,
            user_id=state.get("user_id", ""),
            user_message=user_message,
        )
        return {
            "symptom_entities": symptoms,
            "accumulated_symptoms": merged_symptoms,
            "symptom_episode_active": True,
            "red_flags": flags,
            "backend_commands": diary_commands,
            "clarification_pending": True,
            "clarification_step": state.get("clarification_step") or 0,
            "clarification_question": state.get("clarification_question"),
            "fast_checked": False,
        }

    if has_emergency:
        alert = RedFlagAlert(red_flags=flags, message="⚠️ Позвоните 112 немедленно!")
        alert_cmd = BackendCommand(command_type="ALERT_DOCTOR", payload=alert.model_dump()).model_dump()
        diary_commands = _build_diary_commands(
            symptoms=symptoms, user_id=state.get("user_id", ""), user_message=user_message,
        )
        emergency_text = (
            "У вас критические показатели. Немедленно позвоните 112 или попросите "
            "кого-то рядом вызвать скорую. Не оставайтесь одни."
        )
        write({"type": "alert", "payload": alert.model_dump()})
        write({"type": "token", "content": emergency_text})
        if diary_commands:
            write({"type": "commands", "payload": diary_commands})
        return {
            "symptom_entities": symptoms,
            "accumulated_symptoms": merged_symptoms,
            "symptom_episode_active": True,
            "red_flags": flags,
            "response_text": emergency_text,
            "response_type": ResponseType.alert,
            "alert_payload": alert,
            "messages": history + [{"role": "assistant", "content": emergency_text}],
            "backend_commands": [alert_cmd] + diary_commands,
        }

    if has_urgent:
        urgent_text = (
            "Некоторые показатели требуют внимания врача. "
            "Рекомендую обратиться к врачу сегодня."
        )
        diary_commands = _build_diary_commands(
            symptoms=symptoms, user_id=state.get("user_id", ""), user_message=user_message,
        )
        write({"type": "token", "content": urgent_text})
        write({"type": "alert", "payload": RedFlagAlert(red_flags=flags, message=urgent_text).model_dump()})
        if diary_commands:
            write({"type": "commands", "payload": diary_commands})
        return {
            "symptom_entities": symptoms,
            "accumulated_symptoms": merged_symptoms,
            "symptom_episode_active": True,
            "red_flags": flags,
            "response_text": urgent_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": urgent_text}],
            "backend_commands": diary_commands,
        }

    system_prompt = WELLBEING_SYSTEM_PROMPT + patient_ctx
    chat_messages = [{"role": "system", "content": system_prompt}] + history
    full_text = ""
    try:
        async for token in llm_handler.stream(chat_messages):
            full_text += token
            write({"type": "token", "content": token})
    except Exception as e:
        logger.error(f"Wellbeing stream error: {e}")
        full_text = "Спасибо, что поделились своим самочувствием."
        write({"type": "token", "content": full_text})

    diary_commands = _build_diary_commands(
        symptoms=symptoms, user_id=state.get("user_id", ""), user_message=user_message,
    )
    if diary_commands:
        write({"type": "commands", "payload": diary_commands})

    return {
        "symptom_entities": symptoms,
        "accumulated_symptoms": merged_symptoms,
        "symptom_episode_active": True,
        "red_flags": flags,
        "response_text": full_text,
        "response_type": ResponseType.text,
        "messages": history + [{"role": "assistant", "content": full_text}],
        "backend_commands": diary_commands,
    }