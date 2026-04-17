import asyncio
import logging
import json
from typing import Dict, List, Any, AsyncGenerator, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer

from app.config import settings
from app.schemas import (
    GraphState, IntentEnum, ResponseType, SymptomsData, SymptomEntity,
    RedFlag, RedFlagAlert, BackendCommand, Button, UserContext, MedicationTaken,
    SourceReference, ResponseMeta, ClarificationTriageState, TriageQAPair, TriageKnown
)
from app.prompts import (
    CLASSIFIER_SYSTEM_PROMPT, WELLBEING_SYSTEM_PROMPT, WELLBEING_EXTRACT_PROMPT,
    DATA_INPUT_SYSTEM_PROMPT, EDUCATION_SYSTEM_PROMPT, EMOTIONAL_SYSTEM_PROMPT,
    REMINDER_SYSTEM_PROMPT, CLARIFICATION_SYSTEM_PROMPT, CLARIFICATION_RESPONSE_PROMPT
)
from app.rules import evaluate_red_flags, STROKE_SYMPTOMS
from app.rag import RAGService
from app.llm import LLMHandler

logger = logging.getLogger(__name__)

STROKE_SYMPTOM_KEYS = {
    "numbness", "arm_or_leg_weakness", "face_asymmetry",
    "balance_loss", "vision_changes", "speech_change",
    "dysphagia", "confusion", "disorientation"
}

# ── helpers ──────────────────────────────────────────────────────────────────

def safe_json(text: str) -> Dict:
    try:
        if not text:
            return {}
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            inner = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            stripped = inner.strip()
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {}


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
        key=lambda w: wellbeing_rank.get(w, 1)
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
    has_emergency = any(f.level == "emergency" for f in red_flags)
    if has_emergency:
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
    if score >= 0.70:
        return "high"
    elif score >= 0.55:
        return "medium"
    elif score >= 0.35:
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
    any_present = any(e.present for e in symptoms.symptoms.values())
    return "normal" if any_present else "good"


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
                    }
                }
            }
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
                }
            }
        ).model_dump())

    for med in symptoms.medications_taken:
        commands.append(BackendCommand(
            command_type="SAVE_DIARY_ENTRY",
            payload={
                "user_id": user_id,
                "entry_type": "medication",
                "entry_json": med.model_dump()
            }
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
    llm_handler: LLMHandler
) -> str:
    """Expand short patient answer into full sentence using question context."""
    if len(answer.split()) > 5:  # already long enough
        return answer
    try:
        expanded = await llm_handler.chat_completion([
            {
                "role": "user",
                "content": (
                    f"Вопрос был задан пациенту: «{question}»\n"
                    f"Пациент ответил: «{answer}»\n"
                    "Перефразируй ответ пациента в одно полное информативное предложение, "
                    "сохраняя смысл. Только предложение, без пояснений."
                )
            }
        ])
        logger.info(f"Expanded answer: «{answer}» → «{expanded}»")
        return expanded.strip()
    except Exception as e:
        logger.warning(f"Answer expansion failed: {e}")
        return answer

# ── graph builder ─────────────────────────────────────────────────────────────

def build_workflow(llm_handler: LLMHandler, rag_service: RAGService):

    async def classifier_node(state: GraphState) -> Dict[str, Any]:
        user_ctx = _get_user_context(state)
        patient_ctx = _build_patient_context_str(user_ctx)
        system_prompt = CLASSIFIER_SYSTEM_PROMPT + patient_ctx

        history: List[Dict[str, str]] = list(state.get("messages") or [])
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_message"]}
        ]

        try:
            resp_text = await llm_handler.chat_completion(
                messages,
                response_format={"type": "json_object"},
            )
            logger.info(f"Classifier raw: {resp_text!r}")
            data = safe_json(resp_text)
            logger.info(f"Classifier parsed: {data}")
        except Exception as e:
            logger.error(f"Classifier FAILED: {type(e).__name__}: {e}")
            return {
                "intent": IntentEnum.off_topic,
                "intent_confidence": 0.0,
                "messages": history + [{"role": "user", "content": state["user_message"]}]
            }

        intent_str = data.get("intent", "off_topic")
        try:
            intent = IntentEnum(intent_str)
        except ValueError:
            logger.warning(f"Unknown intent '{intent_str}', falling back to off_topic")
            intent = IntentEnum.off_topic

        reset = _should_reset_episode(state, intent)
        if reset:
            logger.info(f"Symptom episode reset: intent switched to {intent}")

        return {
            "intent": intent,
            "intent_confidence": data.get("confidence", 1.0),
            "messages": history + [{"role": "user", "content": state["user_message"]}],
            "accumulated_symptoms": None if reset else state.get("accumulated_symptoms"),
            "symptom_episode_active": False if reset else state.get("symptom_episode_active"),
            "fast_checked": False if reset else state.get("fast_checked"),
            "clarification_pending": False if reset else state.get("clarification_pending"),
        }

    async def wellbeing_node(state: GraphState) -> Dict[str, Any]:
        write = get_stream_writer()
        user_message = state["user_message"]
        user_ctx = _get_user_context(state)
        patient_ctx = _build_patient_context_str(user_ctx)

        extract_messages = [
            {"role": "system", "content": WELLBEING_EXTRACT_PROMPT + patient_ctx},
            {"role": "user", "content": user_message}
        ]

        logger.info("Wellbeing: firing single combined extraction request")
        try:
            extract_resp = await llm_handler.chat_completion(
                extract_messages, response_format={"type": "json_object"}
            )
        except Exception as e:
            logger.error(f"Extraction FAILED: {type(e).__name__}: {e}")
            extract_resp = ""

        extract_data = safe_json(extract_resp)
        logger.info(f"Extraction raw: {extract_data}")

        bp_data = extract_data.get("blood_pressure") or {}
        bp_obj = None
        if bp_data.get("systolic") or bp_data.get("diastolic"):
            bp_obj = {
                "systolic": bp_data.get("systolic"),
                "diastolic": bp_data.get("diastolic"),
                "pulse": bp_data.get("pulse"),
            }

        merged = {
            "symptoms": extract_data.get("symptoms", {}),
            "general_wellbeing": "normal",
            "blood_pressure": bp_obj,
            "medications_taken": extract_data.get("medications_taken", []),
        }

        try:
            symptoms = SymptomsData(**merged)
        except Exception as e:
            logger.error(f"SymptomsData parse FAILED: {e}, merged={merged}")
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
            f"Accumulated after merge: {list(merged_symptoms.symptoms.keys())} | "
            f"is_new flags: { {k: v.is_new for k, v in merged_symptoms.symptoms.items()} }"
        )

        known_symptoms = (user_ctx.known_symptoms or []) if user_ctx else []
        stroke_date = user_ctx.stroke_date if user_ctx else None
        fast_checked = False
        flags = evaluate_red_flags(
            merged_symptoms,
            known_symptoms=known_symptoms,
            stroke_date=stroke_date,
            fast_checked=fast_checked,
        )
        has_emergency = any(f.level == "emergency" for f in flags)
        has_urgent = any(f.level == "urgent" for f in flags)
        history: List[Dict[str, str]] = list(state.get("messages") or [])

        has_stroke_emergency = any(
            f.level == "emergency" and f.name in STROKE_SYMPTOM_KEYS
            for f in flags
        )

        logger.info(
            f"Flags: {[f.name + ':' + f.level for f in flags]} | "
            f"has_emergency={has_emergency} | "
            f"has_stroke_emergency={has_stroke_emergency} | "
            f"fast_checked={fast_checked}"
        )

        if _has_stroke_symptoms(merged_symptoms) and not fast_checked:
            logger.info("Stroke symptoms detected but fast_checked=False — deferring to clarification_node")
            diary_commands = _build_diary_commands(
                symptoms=symptoms,
                user_id=state.get("user_id", ""),
                user_message=user_message,
            )
            # Preserve existing clarification progress — don't reset if already in progress
            existing_step = state.get("clarification_step") or 0
            return {
                "symptom_entities": symptoms,
                "accumulated_symptoms": merged_symptoms,
                "symptom_episode_active": True,
                "red_flags": flags,
                "backend_commands": diary_commands,
                "clarification_pending": True,
                "clarification_step": existing_step,
                "clarification_question": state.get("clarification_question"),
                "fast_checked": False,
            }

        if has_emergency:
            alert_msg = "⚠️ Позвоните 112 немедленно!"
            alert = RedFlagAlert(red_flags=flags, message=alert_msg)
            alert_cmd = BackendCommand(
                command_type="ALERT_DOCTOR",
                payload=alert.model_dump()
            ).model_dump()

            diary_commands = _build_diary_commands(
                symptoms=symptoms,
                user_id=state.get("user_id", ""),
                user_message=user_message,
            )

            write({"type": "alert", "payload": alert.model_dump()})
            emergency_text = (
                "У вас критические показатели. Немедленно позвоните 112 или попросите "
                "кого-то рядом вызвать скорую. Не оставайтесь одни."
            )
            write({"type": "token", "content": emergency_text})
            if diary_commands:
                write({"type": "commands", "payload": diary_commands})

            all_commands = [alert_cmd] + diary_commands
            return {
                "symptom_entities": symptoms,
                "accumulated_symptoms": merged_symptoms,
                "symptom_episode_active": True,
                "red_flags": flags,
                "response_text": emergency_text,
                "response_type": ResponseType.alert,
                "alert_payload": alert,
                "messages": history + [{"role": "assistant", "content": emergency_text}],
                "backend_commands": all_commands,
            }

        if has_urgent:
            urgent_text = (
                "Некоторые показатели требуют внимания врача. "
                "Рекомендую обратиться к врачу сегодня."
            )
            diary_commands = _build_diary_commands(
                symptoms=symptoms,
                user_id=state.get("user_id", ""),
                user_message=user_message,
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
            async for token in llm_handler.chat_completion_stream(chat_messages):
                full_text += token
                write({"type": "token", "content": token})
        except Exception as e:
            logger.error(f"Wellbeing response stream error: {e}")
            full_text = "Спасибо, что поделились своим самочувствием."
            write({"type": "token", "content": full_text})

        diary_commands = _build_diary_commands(
            symptoms=symptoms,
            user_id=state.get("user_id", ""),
            user_message=user_message,
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

    async def clarification_node(state: GraphState) -> Dict[str, Any]:
        write = get_stream_writer()
        history: List[Dict[str, str]] = list(state.get("messages") or [])

        # When routed directly (bypassing classifier_node), current user message
        # is not yet in history — add it now
        user_message = state.get("user_message", "")
        if user_message and (not history or history[-1].get("content") != user_message):
            history = history + [{"role": "user", "content": user_message}]

        symptoms: SymptomsData = state.get("symptom_entities")

        symptoms_summary = {
            k: {
                "present": e.present,
                "is_new": e.is_new,
                "is_worsening": e.is_worsening,
                "side": e.side,
            }
            for k, e in symptoms.symptoms.items() if e.present
        }

        questions_asked = state.get("clarification_step") or 0
        if not isinstance(questions_asked, int):
            questions_asked = 0

        # ── Build / update structured triage state ────────────────────────────
        raw_triage = state.get("clarification_triage_state")
        if isinstance(raw_triage, dict):
            try:
                triage_state = ClarificationTriageState(**raw_triage)
            except Exception as e:
                logger.warning(f"ClarificationTriageState parse failed: {e}")
                triage_state = ClarificationTriageState(symptoms=symptoms_summary)
        elif isinstance(raw_triage, ClarificationTriageState):
            triage_state = raw_triage
        else:
            triage_state = ClarificationTriageState(symptoms=symptoms_summary)

        # Always sync symptoms and step
        triage_state.symptoms = symptoms_summary
        triage_state.questions_asked = questions_asked

        # ── Expand and record latest Q&A pair ─────────────────────────────────
        last_question = state.get("clarification_question") or ""
        last_patient_answer = next(
            (m["content"] for m in reversed(history) if m["role"] == "user"),
            ""
        )

        if last_question and last_patient_answer:
            already_recorded = any(
                qa.question == last_question for qa in triage_state.qa_pairs
            )
            if not already_recorded:
                expanded = last_patient_answer
                if len(last_patient_answer.split()) <= 5:
                    try:
                        expanded = await llm_handler.chat_completion([
                            {
                                "role": "user",
                                "content": (
                                    f"Вопрос был задан пациенту: «{last_question}»\n"
                                    f"Пациент ответил: «{last_patient_answer}»\n"
                                    "Перефразируй ответ пациента в одно полное информативное "
                                    "предложение, сохраняя смысл. Только предложение, без пояснений."
                                )
                            }
                        ])
                        expanded = expanded.strip()
                        logger.info(f"Expanded: «{last_patient_answer}» → «{expanded}»")
                    except Exception as e:
                        logger.warning(f"Answer expansion failed: {e}")

                triage_state.qa_pairs.append(TriageQAPair(
                    question=last_question,
                    answer=last_patient_answer,
                    expanded=expanded,
                ))

        # ── Build compact prompt ───────────────────────────────────────────────
        system_with_context = (
                CLARIFICATION_SYSTEM_PROMPT
                + f"\n\nТекущее состояние триажа (JSON):\n{triage_state.model_dump_json(indent=2)}"
        )

        triage_messages = [
            {"role": "system", "content": system_with_context},
            {"role": "user", "content": "Проанализируй состояние триажа и верни JSON."},
        ]

        try:
            raw = await llm_handler.chat_completion(
                triage_messages,
                response_format={"type": "json_object"}
            )
            result = safe_json(raw)
            logger.info(f"Clarification triage result: {result}")
        except Exception as e:
            logger.error(f"Clarification triage error: {e}")
            result = {}

        # Retry if empty
        if not result.get("action"):
            logger.warning("Clarification empty — retrying")
            try:
                raw2 = await llm_handler.chat_completion(
                    triage_messages,
                    response_format={"type": "json_object"}
                )
                result = safe_json(raw2)
                logger.info(f"Clarification retry result: {result}")
            except Exception as e:
                logger.error(f"Clarification retry failed: {e}")

        if not result.get("action"):
            logger.error("Clarification: both attempts failed — forcing done")
            result = {
                "action": "done",
                "conclusion": {
                    "is_emergency": False,
                    "fast_positive": False,
                    "is_new": None,
                    "relief_on_movement": None,
                    "reasoning": "Недостаточно данных — рекомендуем обратиться к врачу."
                }
            }

        action = result.get("action", "ask")

        if action == "done" or questions_asked >= 3:
            conclusion = result.get("conclusion") or {}
            is_emergency = conclusion.get("is_emergency", False)
            fast_positive = conclusion.get("fast_positive", False)
            is_new = conclusion.get("is_new")
            relief_on_movement = conclusion.get("relief_on_movement")
            reasoning = conclusion.get("reasoning", "")

            if fast_positive:
                for key in ("face_asymmetry", "arm_or_leg_weakness"):
                    if key not in symptoms.symptoms or not symptoms.symptoms[key].present:
                        symptoms.symptoms[key] = SymptomEntity(present=True, is_new=True)

            user_ctx = _get_user_context(state)
            known_symptoms = list(user_ctx.known_symptoms or []) if user_ctx else []
            stroke_date = user_ctx.stroke_date if user_ctx else None

            flags = evaluate_red_flags(
                symptoms,
                known_symptoms=known_symptoms,
                stroke_date=stroke_date,
                fast_checked=True,
            )

            if relief_on_movement is True and not fast_positive:
                primary_symptom = next(
                    (k for k, e in symptoms.symptoms.items() if e.present and k in STROKE_SYMPTOMS),
                    None
                )
                if primary_symptom:
                    flags = [f for f in flags if f.name != primary_symptom]

            has_emergency = any(f.level == "emergency" for f in flags) or is_emergency

            response_prompt = CLARIFICATION_RESPONSE_PROMPT.format(
                is_emergency=has_emergency,
                fast_positive=fast_positive,
                is_new=is_new,
                relief_on_movement=relief_on_movement,
                reasoning=reasoning,
            )
            try:
                response_text = await llm_handler.chat_completion(
                    [{"role": "user", "content": response_prompt}]
                )
            except Exception as e:
                logger.error(f"Clarification response generation error: {e}")
                response_text = "Пожалуйста, обратитесь к врачу для оценки вашего состояния."

            if has_emergency:
                alert = RedFlagAlert(red_flags=flags, message="⚠️ Позвоните 112 немедленно!")
                write({"type": "alert", "payload": alert.model_dump()})

            write({"type": "token", "content": response_text})

            return {
                "response_text": response_text,
                "response_type": ResponseType.alert if has_emergency else ResponseType.text,
                "messages": history + [{"role": "assistant", "content": response_text}],
                "backend_commands": [],
                "clarification_pending": False,
                "clarification_step": 0,
                "clarification_question": None,
                "clarification_triage_state": None,
                "fast_checked": True,
                "symptom_entities": symptoms,
                "red_flags": flags,
            }

        # Ask next question
        question = result.get("question") or "Расскажите подробнее о своих симптомах."
        write({"type": "token", "content": question})
        return {
            "response_text": question,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": question}],
            "backend_commands": [],
            "clarification_pending": True,
            "clarification_step": questions_asked + 1,
            "clarification_question": question,
            "clarification_triage_state": triage_state,
            "symptom_entities": symptoms,
        }

    async def data_input_node(state: GraphState) -> Dict[str, Any]:
        write = get_stream_writer()
        messages = [
            {"role": "system", "content": DATA_INPUT_SYSTEM_PROMPT},
            {"role": "user", "content": state["user_message"]}
        ]
        resp_text = ""
        try:
            resp_text = await llm_handler.chat_completion(
                messages,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.error(f"Data Input Error: {e}")

        data = safe_json(resp_text)
        user_id = state.get("user_id")
        commands = []

        if data.get("systolic_bp") or data.get("diastolic_bp"):
            commands.append(BackendCommand(
                command_type="SAVE_DIARY_ENTRY",
                payload={
                    "user_id": user_id,
                    "entry_type": "blood_pressure",
                    "entry_json": {
                        "systolic": data.get("systolic_bp"),
                        "diastolic": data.get("diastolic_bp"),
                        "pulse": data.get("pulse"),
                    }
                }
            ).model_dump())

        if data.get("blood_sugar") is not None:
            commands.append(BackendCommand(
                command_type="SAVE_DIARY_ENTRY",
                payload={
                    "user_id": user_id,
                    "entry_type": "blood_test",
                    "entry_json": {
                        "blood_sugar": data.get("blood_sugar"),
                        "user_message_raw": state["user_message"],
                    }
                }
            ).model_dump())

        # Red flag check for BP
        bp_symptoms = SymptomsData(
            blood_pressure={
                "systolic": data.get("systolic_bp"),
                "diastolic": data.get("diastolic_bp"),
                "pulse": data.get("pulse"),
            }
        )
        user_ctx = _get_user_context(state)
        if user_ctx:
            bp_symptoms.age_category = user_ctx.age_category

        flags = evaluate_red_flags(bp_symptoms)
        has_emergency = any(f.level == "emergency" for f in flags)
        has_urgent = any(f.level == "urgent" for f in flags)
        history: List[Dict[str, str]] = list(state.get("messages") or [])

        if has_emergency:
            alert = RedFlagAlert(red_flags=flags, message="⚠️ Позвоните 112 немедленно!")
            alert_cmd = BackendCommand(
                command_type="ALERT_DOCTOR",
                payload=alert.model_dump()
            ).model_dump()
            commands.append(alert_cmd)
            write({"type": "commands", "payload": commands})
            write({"type": "alert", "payload": alert.model_dump()})
            response_text = (
                "Давление критически высокое. Немедленно позвоните 112 "
                "или попросите кого-то рядом вызвать скорую."
            )
            write({"type": "token", "content": response_text})
            return {
                "response_text": response_text,
                "response_type": ResponseType.alert,
                "messages": history + [{"role": "assistant", "content": response_text}],
                "backend_commands": commands,
                "red_flags": flags,
            }

        if has_urgent:
            alert = RedFlagAlert(red_flags=flags, message="Давление выше целевого")
            write({"type": "commands", "payload": commands})
            write({"type": "alert", "payload": alert.model_dump()})
            response_text = f"Данные сохранены. {flags[0].description} — {flags[0].target_info}."
            write({"type": "token", "content": response_text})
            return {
                "response_text": response_text,
                "response_type": ResponseType.text,
                "messages": history + [{"role": "assistant", "content": response_text}],
                "backend_commands": commands,
                "red_flags": flags,
            }

        if commands:
            write({"type": "commands", "payload": commands})

        response_text = "Данные сохранены в дневник."
        write({"type": "token", "content": response_text})
        return {
            "response_text": response_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": response_text}],
            "backend_commands": commands,
        }

    async def education_node(state: GraphState) -> Dict[str, Any]:
        write = get_stream_writer()
        collections = ["stroke_clinrecs_gigaembed"]
        docs = []
        scores = []
        user_ctx = _get_user_context(state)
        subtype = user_ctx.stroke_toast_subtype if user_ctx else None

        for coll in collections:
            try:
                info = await rag_service.qdrant_client.get_collection(coll)
                logger.info(f"Collection '{coll}' points_count={info.points_count}")
                logger.info(f"Vectors config: {info.config.params.vectors}")
            except Exception as e:
                logger.error(f"Failed to get collection info for '{coll}': {e}")

            res = await rag_service.search(coll, state["user_message"], stroke_subtype=subtype)
            docs.extend(res)
            scores.extend([d["score"] for d in res])

        logger.info(f"RAG Results: {docs}")
        rag_conf = max(scores) if scores else 0.0
        confidence_label = _build_confidence_label(rag_conf)

        sources = [
            SourceReference(source=d.get("source", ""))
            for d in docs[:5]
            if d.get("source")
        ]

        intent = state.get("intent", IntentEnum.education)

        if confidence_label == "insufficient":
            fallback_text = "К сожалению, точной информации не найдено. Вот общая памятка."
            meta = ResponseMeta(
                confidence=rag_conf,
                confidence_label=confidence_label,
                sources=[],
                intent=str(intent),
                used_rag=True,
            )
            write({"type": "buttons", "payload": [Button(label="Общая памятка", href="/learn").model_dump()]})
            write({"type": "token", "content": fallback_text})
            write({"type": "sources", "payload": meta.model_dump()})
            return {
                "response_text": fallback_text,
                "response_type": ResponseType.text_with_buttons,
                "buttons": [Button(label="Общая памятка", href="/learn")],
                "backend_commands": [],
                "response_meta": meta,
            }

        context = "\n\n".join([d["content"] for d in docs[:5]])
        patient_ctx = _build_patient_context_str(user_ctx)
        sys_prompt = f"{EDUCATION_SYSTEM_PROMPT}\nКонтекст: {context}{patient_ctx}"
        history: List[Dict[str, str]] = list(state.get("messages") or [])
        messages = [{"role": "system", "content": sys_prompt}] + history
        full_text = ""
        try:
            async for token in llm_handler.chat_completion_stream(messages):
                full_text += token
                write({"type": "token", "content": token})
        except Exception as e:
            logger.error(f"Education Stream Error: {e}")
            full_text = "Произошла ошибка при генерации ответа."

        meta = ResponseMeta(
            confidence=rag_conf,
            confidence_label=confidence_label,
            sources=sources,
            intent=str(intent),
            used_rag=True,
        )
        write({"type": "sources", "payload": meta.model_dump()})

        return {
            "response_text": full_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": full_text}],
            "backend_commands": [],
            "response_meta": meta,
        }

    async def emotional_node(state: GraphState) -> Dict[str, Any]:
        write = get_stream_writer()
        patient_ctx = _build_patient_context_str(_get_user_context(state))
        system_prompt = EMOTIONAL_SYSTEM_PROMPT + patient_ctx
        history: List[Dict[str, str]] = list(state.get("messages") or [])
        messages = [{"role": "system", "content": system_prompt}] + history
        full_text = ""
        try:
            async for token in llm_handler.chat_completion_stream(messages):
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
            "backend_commands": []
        }

    async def reminder_node(state: GraphState) -> Dict[str, Any]:
        write = get_stream_writer()
        patient_ctx = _build_patient_context_str(_get_user_context(state))
        system_prompt = REMINDER_SYSTEM_PROMPT + patient_ctx
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_message"]}
        ]
        resp_text = ""
        try:
            resp_text = await llm_handler.chat_completion(
                messages,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.error(f"Reminder error: {e}")

        data = safe_json(resp_text)
        cmd = BackendCommand(
            command_type="UPSERT_REMINDER",
            payload=data
        ).model_dump()
        write({"type": "commands", "payload": [cmd]})

        response_text = "Напоминание сохранено."
        write({"type": "token", "content": response_text})

        history: List[Dict[str, str]] = list(state.get("messages") or [])
        return {
            "response_text": response_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": response_text}],
            "backend_commands": [cmd]
        }

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
            "backend_commands": []
        }

    async def entry_router_node(state: GraphState) -> Dict[str, Any]:
        logger.info(
            f"entry_router_node state: "
            f"clarification_pending={state.get('clarification_pending')}, "
            f"clarification_step={state.get('clarification_step')}, "
            f"clarification_question={state.get('clarification_question')!r}"
        )
        return {}

    def route_entry(state: GraphState) -> str:
        if (
                state.get("clarification_pending")
                or (state.get("clarification_step") or 0) > 0
                or state.get("clarification_question")  # most reliable fallback
        ):
            logger.info(
                f"route_entry → clarification_node "
                f"(pending={state.get('clarification_pending')}, "
                f"step={state.get('clarification_step')}, "
                f"question={state.get('clarification_question')!r})"
            )
            return "clarification_node"
        return "classifier_node"

    def route_by_intent(state: GraphState) -> str:
        intent = state.get("intent", IntentEnum.off_topic)
        mapping = {
            IntentEnum.wellbeing_check: "wellbeing_node",
            IntentEnum.data_input: "data_input_node",
            IntentEnum.education: "education_node",
            IntentEnum.social_navigation: "education_node",
            IntentEnum.emotional_support: "emotional_node",
            IntentEnum.reminder_management: "reminder_node",
            IntentEnum.off_topic: "off_topic_node"
        }
        return mapping.get(intent, "off_topic_node")

    def route_after_wellbeing(state: GraphState) -> str:
        if state.get("clarification_pending"):
            return "clarification_node"
        red_flags = state.get("red_flags") or []
        if any(f.level in ("emergency", "urgent") for f in red_flags):
            return "__end__"
        return "education_node"

    workflow = StateGraph(GraphState)

    workflow.add_node("entry_router_node", entry_router_node)
    workflow.add_node("classifier_node", classifier_node)
    workflow.add_node("wellbeing_node", wellbeing_node)
    workflow.add_node("clarification_node", clarification_node)
    workflow.add_node("data_input_node", data_input_node)
    workflow.add_node("education_node", education_node)
    workflow.add_node("emotional_node", emotional_node)
    workflow.add_node("reminder_node", reminder_node)
    workflow.add_node("off_topic_node", off_topic_node)

    workflow.add_edge(START, "entry_router_node")
    workflow.add_conditional_edges("entry_router_node", route_entry, {
        "classifier_node": "classifier_node",
        "clarification_node": "clarification_node",
    })
    workflow.add_conditional_edges("classifier_node", route_by_intent, {
        "wellbeing_node": "wellbeing_node",
        "data_input_node": "data_input_node",
        "education_node": "education_node",
        "emotional_node": "emotional_node",
        "reminder_node": "reminder_node",
        "off_topic_node": "off_topic_node"
    })
    workflow.add_conditional_edges("wellbeing_node", route_after_wellbeing, {
        "clarification_node": "clarification_node",
        "education_node": "education_node",
        "__end__": END,
    })

    workflow.add_edge("clarification_node", END)
    workflow.add_edge("data_input_node", END)
    workflow.add_edge("education_node", END)
    workflow.add_edge("emotional_node", END)
    workflow.add_edge("reminder_node", END)
    workflow.add_edge("off_topic_node", END)

    return workflow.compile(checkpointer=MemorySaver())


async def run_graph(
    input_data: Dict[str, Any],
    config: Dict[str, Any],
    *,
    graph
) -> AsyncGenerator[Dict, None]:
    async for event in graph.astream(input_data, config, stream_mode="custom"):
        if isinstance(event, dict):
            yield event