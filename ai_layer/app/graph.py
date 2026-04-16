import asyncio
import logging
import json
from typing import Dict, List, Any, AsyncGenerator, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer

from app.config import settings
from app.schemas import (
    GraphState, IntentEnum, ResponseType, SymptomsData, RedFlag, RedFlagAlert,
    BackendCommand, Button, UserContext, MedicationTaken,
    SourceReference, ResponseMeta
)
from app.prompts import (
    CLASSIFIER_SYSTEM_PROMPT, WELLBEING_SYSTEM_PROMPT, SYMPTOM_EXTRACT_PROMPT,
    BP_EXTRACT_PROMPT, MEDICATION_EXTRACT_PROMPT, DATA_INPUT_SYSTEM_PROMPT,
    EDUCATION_SYSTEM_PROMPT, EMOTIONAL_SYSTEM_PROMPT, REMINDER_SYSTEM_PROMPT
)
from app.rules import evaluate_red_flags
from app.rag import RAGService
from app.llm import LLMHandler

logger = logging.getLogger(__name__)


# ─────────────────────────── helpers ────────────────────────────

def safe_json(text: str) -> Dict:
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        logger.warning(f"safe_json failed to parse: {text[:120]!r}")
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


def _enrich_symptoms_with_history(
    symptoms: SymptomsData,
    known_symptoms: List[str],
) -> SymptomsData:
    for sym_key, entity in symptoms.symptoms.items():
        if entity.present and sym_key not in known_symptoms:
            entity.is_new = True
            logger.info(f"Symptom '{sym_key}' marked as NEW (not in history)")
    return symptoms

def _build_confidence_label(score: float) -> str:
    if score >= 0.75:
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

    # 1. SYMPTOM entry
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

    # 2. BLOOD PRESSURE entry
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

    # 3. MEDICATION entries — one per medication
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


# ─────────────────────────── graph builder ────────────────────────────

def build_workflow(llm_handler: LLMHandler, rag_service: RAGService):

    async def classifier_node(state: GraphState) -> Dict[str, Any]:
        user_ctx = _get_user_context(state)
        patient_ctx = _build_patient_context_str(user_ctx)
        system_prompt = CLASSIFIER_SYSTEM_PROMPT + patient_ctx

        history: List[Dict[str, str]] = list(state.get("messages") or [])
        messages = [{"role": "system", "content": system_prompt}] + history + [
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

        return {
            "intent": intent,
            "intent_confidence": data.get("confidence", 1.0),
            "messages": history + [{"role": "user", "content": state["user_message"]}]
        }
    async def wellbeing_node(state: GraphState) -> Dict[str, Any]:
        write = get_stream_writer()
        user_message = state["user_message"]
        user_ctx = _get_user_context(state)
        patient_ctx = _build_patient_context_str(user_ctx)

        # ── 3 parallel extractions ──
        symptom_messages = [
            {"role": "system", "content": SYMPTOM_EXTRACT_PROMPT + patient_ctx},
            {"role": "user", "content": user_message}
        ]
        bp_messages = [
            {"role": "system", "content": BP_EXTRACT_PROMPT},
            {"role": "user", "content": user_message}
        ]
        med_messages = [
            {"role": "system", "content": MEDICATION_EXTRACT_PROMPT},
            {"role": "user", "content": user_message}
        ]

        logger.info("Wellbeing: firing 3 parallel extraction requests")
        results = await asyncio.gather(
            llm_handler.chat_completion(symptom_messages, response_format={"type": "json_object"}),
            llm_handler.chat_completion(bp_messages, response_format={"type": "json_object"}),
            llm_handler.chat_completion(med_messages, response_format={"type": "json_object"}),
            return_exceptions=True
        )

        symptom_resp, bp_resp, med_resp = results

        if isinstance(symptom_resp, Exception):
            logger.error(f"Symptom extraction FAILED: {type(symptom_resp).__name__}: {symptom_resp}")
            symptom_resp = ""
        if isinstance(bp_resp, Exception):
            logger.error(f"BP extraction FAILED: {type(bp_resp).__name__}: {bp_resp}")
            bp_resp = ""
        if isinstance(med_resp, Exception):
            logger.error(f"Medication extraction FAILED: {type(med_resp).__name__}: {med_resp}")
            med_resp = ""

        symptom_data = safe_json(symptom_resp)
        bp_data = safe_json(bp_resp)
        med_data = safe_json(med_resp)

        bp_obj = None
        if bp_data.get("systolic") or bp_data.get("diastolic"):
            bp_obj = {
                "systolic": bp_data.get("systolic"),
                "diastolic": bp_data.get("diastolic"),
                "pulse": bp_data.get("pulse"),
            }

        merged = {
            "symptoms": symptom_data.get("symptoms", {}),
            "general_wellbeing": "normal",
            "blood_pressure": bp_obj,
            "medications_taken": med_data.get("medications_taken", []),
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
            if user_ctx.known_symptoms:
                symptoms = _enrich_symptoms_with_history(symptoms, user_ctx.known_symptoms)

        # ── Evaluate red flags BEFORE streaming any text ──
        flags = evaluate_red_flags(symptoms)
        has_emergency = any(f.level == "emergency" for f in flags)
        has_urgent = any(f.level == "urgent" for f in flags)

        history: List[Dict[str, str]] = list(state.get("messages") or [])

        if has_emergency:
            # Do NOT stream soft reassuring text — send alert immediately
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

            # Stream: alert first, then brief text, then commands
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
                "red_flags": flags,
                "response_text": emergency_text,
                "response_type": ResponseType.alert,
                "alert_payload": alert,
                "messages": history + [{"role": "assistant", "content": emergency_text}],
                "backend_commands": all_commands,
            }

        if has_urgent:
            # Stream a brief cautious text, then buttons
            urgent_text = (
                "Некоторые показатели требуют внимания врача. "
                "Рекомендую обратиться к врачу сегодня."
            )
            buttons = [
                Button(label="Связаться с врачом", payload={"action": "call_doctor"}).model_dump()
            ]
            diary_commands = _build_diary_commands(
                symptoms=symptoms,
                user_id=state.get("user_id", ""),
                user_message=user_message,
            )

            write({"type": "token", "content": urgent_text})
            write({"type": "alert", "payload": RedFlagAlert(red_flags=flags, message=urgent_text).model_dump()})
            write({"type": "buttons", "payload": buttons})
            if diary_commands:
                write({"type": "commands", "payload": diary_commands})

            return {
                "symptom_entities": symptoms,
                "red_flags": flags,
                "response_text": urgent_text,
                "response_type": ResponseType.text_with_buttons,
                "buttons": buttons,
                "messages": history + [{"role": "assistant", "content": urgent_text}],
                "backend_commands": diary_commands,
            }

        # ── No critical flags — stream warm LLM response ──
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
            "red_flags": flags,
            "response_text": full_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": full_text}],
            "backend_commands": diary_commands,
        }

    async def red_flag_node(state: GraphState) -> Dict[str, Any]:
        # red_flag_node is now a passthrough — all logic moved to wellbeing_node
        # Kept in graph for future use (e.g. post-education red flag checks)
        return {
            "red_flags": state.get("red_flags", []),
            "backend_commands": state.get("backend_commands", []),
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

        # Blood pressure → entry_type: "blood_pressure"
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

        # Blood sugar → entry_type: "blood_test" (EntryType.BLOOD_TEST на бэкенде)
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

        if commands:
            write({"type": "commands", "payload": commands})

        response_text = "Данные сохранены в дневник."
        write({"type": "text", "content": response_text})

        history: List[Dict[str, str]] = list(state.get("messages") or [])
        return {
            "response_text": response_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": response_text}],
            "backend_commands": commands
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

                sample = await rag_service.qdrant_client.scroll(
                    collection_name=coll, limit=1,
                    with_payload=True, with_vectors=True
                )
                if sample[0]:
                    p = sample[0][0]
                    test_query = p.payload['content'][50:150].strip()
                    logger.info(f"Test query: {test_query}")
                    test_res = await rag_service.qdrant_client.query_points(
                        collection_name=coll,
                        query=await rag_service.llm_handler.get_embedding(test_query),
                        using="dense",
                        limit=3,
                        score_threshold=0.0,
                        with_payload=False
                    )
                    logger.info(f"Self-search result: {test_res}")
            except Exception as e:
                logger.error(f"Failed to get collection info for '{coll}': {e}")

            res = await rag_service.search(coll, state["user_message"], stroke_subtype=subtype)
            docs.extend(res)
            scores.extend([d["score"] for d in res])

        logger.info(f"RAG Results: {docs}")
        rag_conf = max(scores) if scores else 0.0
        confidence_label = _build_confidence_label(rag_conf)

        # Собираем источники из метаданных
        sources = [
            SourceReference(source=d.get("source", ""))
            for d in docs[:5]
            if d.get("source")
        ]

        intent = state.get("intent", IntentEnum.education)

        if confidence_label == "insufficient":
            fallback_text = "К сожалению, точной информации не найдено. Вот общая памятка."
            buttons = [Button(label="Общая памятка", payload={"action": "guide"}).model_dump()]
            meta = ResponseMeta(
                confidence=rag_conf,
                confidence_label=confidence_label,
                sources=[],
                intent=str(intent),
                used_rag=True,
            )
            write({"type": "buttons", "payload": buttons})
            write({"type": "token", "content": fallback_text})
            write({"type": "sources", "payload": meta.model_dump()})
            return {
                "response_text": fallback_text,
                "response_type": ResponseType.text_with_buttons,
                "buttons": buttons,
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
            write({"type": "text", "content": full_text})

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
        write({"type": "text", "content": response_text})

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
        write({"type": "text", "content": response_text})
        history: List[Dict[str, str]] = list(state.get("messages") or [])
        return {
            "response_text": response_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": response_text}],
            "backend_commands": []
        }

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
        # red flags already handled inside wellbeing_node
        # go to red_flag_node only if there are unprocessed symptoms (passthrough)
        symptoms = state.get("symptom_entities")
        if symptoms and (symptoms.symptoms or symptoms.blood_pressure):
            return "red_flag_node"
        return END

    workflow = StateGraph(GraphState)

    workflow.add_node("classifier_node", classifier_node)
    workflow.add_node("wellbeing_node", wellbeing_node)
    workflow.add_node("red_flag_node", red_flag_node)
    workflow.add_node("data_input_node", data_input_node)
    workflow.add_node("education_node", education_node)
    workflow.add_node("emotional_node", emotional_node)
    workflow.add_node("reminder_node", reminder_node)
    workflow.add_node("off_topic_node", off_topic_node)

    workflow.add_edge(START, "classifier_node")
    workflow.add_conditional_edges("classifier_node", route_by_intent, {
        "wellbeing_node": "wellbeing_node",
        "data_input_node": "data_input_node",
        "education_node": "education_node",
        "emotional_node": "emotional_node",
        "reminder_node": "reminder_node",
        "off_topic_node": "off_topic_node"
    })
    workflow.add_conditional_edges("wellbeing_node", route_after_wellbeing, {
        "red_flag_node": "red_flag_node",
        END: END
    })

    workflow.add_edge("red_flag_node", END)
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