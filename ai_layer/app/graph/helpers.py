import logging
from typing import List, Optional

from app.schemas import (
    GraphState, IntentEnum, SymptomsData, SymptomEntity,
    BackendCommand, UserContext,
)
from app.llm import LLMHandler

logger = logging.getLogger(__name__)

STROKE_SYMPTOM_KEYS = {
    "numbness", "arm_or_leg_weakness", "face_asymmetry",
    "balance_loss", "vision_changes", "speech_change",
    "dysphagia", "confusion", "disorientation",
}


def _get_user_context(state: GraphState) -> Optional[UserContext]:
    ctx = state.get("user_context")
    if ctx is None:
        return None
    if isinstance(ctx, dict):
        try:
            return UserContext(**ctx) if ctx else None
        except Exception:
            return None
    return ctx


def _build_patient_context_str(user_context: Optional[UserContext]) -> str:
    if not user_context:
        return ""
    parts = []
    if user_context.stroke_type:
        parts.append(f"Тип инсульта: {user_context.stroke_type}")
    if user_context.stroke_toast_subtype:
        parts.append(f"Подтип инсульта: {user_context.stroke_toast_subtype}")
    if user_context.medications:
        med_names = ", ".join(m.name for m in user_context.medications)
        parts.append(f"Принимаемые препараты: {med_names}")
    if user_context.role and user_context.role != "patient":
        parts.append(f"Роль пользователя: {user_context.role}")
    if not parts:
        return ""
    return "\n\n[Контекст пациента]\n" + "\n".join(parts)


def _merge_symptoms(base: Optional[SymptomsData], new: SymptomsData) -> SymptomsData:
    if base is None:
        return new
    merged_symptoms = dict(base.symptoms)
    for key, new_entity in new.symptoms.items():
        if new_entity.resolved:
            merged_symptoms.pop(key, None)
            logger.info(f"Symptom '{key}' resolved – removed from accumulated")
            continue
        if not new_entity.present:
            continue
        if key in merged_symptoms:
            old = merged_symptoms[key]
            merged_symptoms[key] = SymptomEntity(
                present=True,
                intensity=new_entity.intensity if new_entity.intensity is not None else old.intensity,
                side=new_entity.side if new_entity.side is not None else old.side,
                value=new_entity.value if new_entity.value is not None else old.value,
                is_new=new_entity.is_new if new_entity.is_new is not None else old.is_new,
                is_worsening=new_entity.is_worsening if new_entity.is_worsening is not None else old.is_worsening,
                has_suicidality=old.has_suicidality or new_entity.has_suicidality,
                resolved=False,
            )
        else:
            merged_symptoms[key] = new_entity

    wellbeing_rank = {"good": 0, "normal": 1, "poor": 2}
    worst_wellbeing = max(
        base.general_wellbeing, new.general_wellbeing,
        key=lambda w: wellbeing_rank.get(w, 1),
    )
    return SymptomsData(
        symptoms=merged_symptoms,
        general_wellbeing=worst_wellbeing,
        free_text=new.free_text,
        blood_pressure=new.blood_pressure or base.blood_pressure,
        medications_taken=base.medications_taken + new.medications_taken,
        age_category=new.age_category or base.age_category,
    )


def _should_reset_episode(state: GraphState, current_intent: IntentEnum) -> bool:
    if current_intent == IntentEnum.wellbeing_check:
        return False
    red_flags = state.get("red_flags") or []
    if any(f.level == "emergency" for f in red_flags):
        return False
    return state.get("symptom_episode_active", False)


def _enrich_symptoms_with_history(
    symptoms: SymptomsData,
    known_symptoms: List[str],
) -> SymptomsData:
    updated = {}
    for sym_key, entity in symptoms.symptoms.items():
        if entity.present and sym_key not in known_symptoms:
            updated[sym_key] = entity.model_copy(update={"is_new": True})
            logger.info(f"Symptom '{sym_key}' marked as NEW")
        else:
            updated[sym_key] = entity
    return symptoms.model_copy(update={"symptoms": updated})


def _build_confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    elif score >= 0.75:
        return "medium"
    elif score >= 0.62:
        return "low"
    return "insufficient"


def _assess_wellbeing_heuristic(symptoms: SymptomsData) -> str:
    bp = symptoms.blood_pressure
    if bp and bp.systolic and bp.systolic >= 180:
        return "poor"
    if bp and bp.systolic and bp.systolic >= 160:
        return "normal"
    if not symptoms.symptoms:
        return "good"
    high_intensity = any(
        e.intensity and e.intensity >= 7
        for e in symptoms.symptoms.values() if e.present
    )
    if high_intensity:
        return "poor"
    return "normal" if any(e.present for e in symptoms.symptoms.values()) else "good"


def _build_diary_commands(
    symptoms: SymptomsData,
    user_id: str,
    user_message: str,
) -> List[dict]:
    commands = []
    present_symptoms = {k: v for k, v in symptoms.symptoms.items() if v.present}
    if present_symptoms:
        commands.append(BackendCommand(
            command_type="SAVE_DIARY_ENTRY",
            payload={
                "user_id": user_id,
                "entry_type": "symptom",
                "entry_json": {
                    "user_message_raw": user_message,
                    "general_wellbeing": symptoms.general_wellbeing,
                    "free_text": user_message,
                    "symptoms": {
                        k: {
                            "present": e.present,
                            "intensity": e.intensity,
                            "side": e.side,
                            "is_new": e.is_new,
                            "is_worsening": e.is_worsening,
                            "has_suicidality": e.has_suicidality,
                            "value": e.value,
                        }
                        for k, e in present_symptoms.items()
                    },
                },
            },
        ).model_dump())

    bp = symptoms.blood_pressure
    if bp and (bp.systolic or bp.diastolic):
        commands.append(BackendCommand(
            command_type="SAVE_DIARY_ENTRY",
            payload={
                "user_id": user_id,
                "entry_type": "blood_pressure",
                "entry_json": {
                    "systolic": bp.systolic,
                    "diastolic": bp.diastolic,
                    "pulse": bp.pulse,
                },
            },
        ).model_dump())

    for med in symptoms.medications_taken:
        commands.append(BackendCommand(
            command_type="SAVE_DIARY_ENTRY",
            payload={
                "user_id": user_id,
                "entry_type": "medication",
                "entry_json": med.model_dump(),
            },
        ).model_dump())

    return commands


def _has_stroke_symptoms(symptoms: SymptomsData) -> bool:
    return any(
        k in STROKE_SYMPTOM_KEYS and v.present
        for k, v in symptoms.symptoms.items()
    )


async def _expand_short_answer(
    question: str,
    answer: str,
    llm_handler: LLMHandler,
) -> str:
    """Разворачивает короткий ответ пациента в полное предложение используя контекст вопроса."""
    if len(answer.split()) > 5:
        return answer
    try:
        expanded = await llm_handler.complete([
            {
                "role": "user",
                "content": (
                    f"Вопрос был задан пациенту: «{question}»\n"
                    f"Пациент ответил: «{answer}»\n"
                    "Перефразируй ответ пациента в одно полное информативное предложение, "
                    "сохраняя смысл. Только предложение, без пояснений."
                ),
            }
        ])
        logger.info(f"Expanded answer: «{answer}» → «{expanded.strip()}»")
        return expanded.strip()
    except Exception as e:
        logger.warning(f"Answer expansion failed: {e}")
        return answer