import logging
import json
from typing import Dict, List, Any, AsyncGenerator, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.schemas import (
    GraphState, IntentEnum, ResponseType, SymptomsData, RedFlag, RedFlagAlert,
    BackendCommand, Button, UserContext
)
from app.prompts import (
    CLASSIFIER_SYSTEM_PROMPT, WELLBEING_SYSTEM_PROMPT, DATA_INPUT_SYSTEM_PROMPT,
    EDUCATION_SYSTEM_PROMPT, EMOTIONAL_SYSTEM_PROMPT, REMINDER_SYSTEM_PROMPT
)
from app.rules import evaluate_red_flags
from app.rag import RAGService
from app.llm import LLMHandler

logger = logging.getLogger(__name__)


def safe_json(text: str) -> Dict:
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        return {}


def _build_patient_context_str(user_context: Optional[UserContext]) -> str:
    if not user_context:
        return ""
    parts = []
    if user_context.stroke_type:
        parts.append(f"Тип инсульта: {user_context.stroke_type}")
    if user_context.stroke_subtype:
        parts.append(f"Подтип инсульта: {user_context.stroke_subtype}")
    if user_context.medications:
        parts.append(f"Принимаемые препараты: {', '.join(user_context.medications)}")
    if user_context.role and user_context.role != "patient":
        parts.append(f"Роль пользователя: {user_context.role}")
    if not parts:
        return ""
    return "\n\n[Контекст пациента]\n" + "\n".join(parts)


def build_workflow(llm_handler: LLMHandler, rag_service: RAGService):

    async def classifier_node(state: GraphState) -> Dict[str, Any]:
        history: List[Dict[str, str]] = list(state.get("messages") or [])
        history.append({"role": "user", "content": state["user_message"]})

        classifier_messages = [
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": state["user_message"]}
        ]
        resp_text = ""
        try:
            resp_text = await llm_handler.chat_completion(classifier_messages, response_format={"type": "json_object"})
        except Exception as e:
            logger.error(f"Classifier Error: {e}")

        data = safe_json(resp_text)
        intent = data.get("intent", "off_topic")
        conf = float(data.get("confidence", 0.0))
        if conf < 0.6:
            intent = "off_topic"
            conf = 0.0
        try:
            intent_enum = IntentEnum(intent)
        except ValueError:
            intent_enum = IntentEnum.off_topic

        return {"intent": intent_enum, "intent_confidence": conf, "messages": history, "backend_commands": [], "red_flags": []}

    async def wellbeing_node(state: GraphState) -> Dict[str, Any]:
        patient_ctx = _build_patient_context_str(state.get("user_context"))
        system_prompt = WELLBEING_SYSTEM_PROMPT + patient_ctx
        history: List[Dict[str, str]] = list(state.get("messages") or [])
        messages = [{"role": "system", "content": system_prompt}] + history[-6:]
        resp_text = ""
        try:
            resp_text = await llm_handler.chat_completion(messages, response_format={"type": "json_object"})
        except Exception as e:
            logger.error(f"Wellbeing Error: {e}")

        try:
            symptoms = SymptomsData(**safe_json(resp_text))
        except Exception:
            symptoms = SymptomsData()

        return {"symptom_entities": symptoms}

    async def red_flag_node(state: GraphState) -> AsyncGenerator[Dict[str, Any], None]:
        symptoms = state.get("symptom_entities")
        flags = evaluate_red_flags(symptoms) if symptoms else []

        update = {
            "red_flags": flags,
            "response_type": ResponseType.text,
            "response_text": "",
            "backend_commands": [],
            "buttons": [],
            "alert_payload": None
        }

        if flags:
            has_emergency = any(f.level == "emergency" for f in flags)
            has_urgent = any(f.level == "urgent" for f in flags)

            if has_emergency or has_urgent:
                msg = "Позвоните 112 немедленно!" if has_emergency else "Обратитесь к врачу сегодня."
                update["response_text"] = msg
                update["response_type"] = ResponseType.alert
                alert = RedFlagAlert(red_flags=flags, message=msg)
                update["alert_payload"] = alert
                update["backend_commands"].append(BackendCommand(command_type="ALERT_DOCTOR", payload=alert.model_dump()).model_dump())
                yield {"type": "alert", "payload": alert.model_dump()}
            else:
                update["response_text"] = f"Обратите внимание: {', '.join(f.name for f in flags)}."
                update["response_type"] = ResponseType.text_with_buttons
                update["buttons"].append(Button(label="Связаться с врачом", payload={"action": "call_doctor"}).model_dump())
                yield {"type": "buttons", "payload": update["buttons"]}
        else:
            update["response_text"] = "Спасибо, что поделились самочувствием."

        history: List[Dict[str, str]] = list(state.get("messages") or [])
        update["messages"] = history + [{"role": "assistant", "content": update["response_text"]}]
        yield {"type": "state_update", **update}

    async def data_input_node(state: GraphState) -> AsyncGenerator[Dict[str, Any], None]:
        messages = [
            {"role": "system", "content": DATA_INPUT_SYSTEM_PROMPT},
            {"role": "user", "content": state["user_message"]}
        ]
        resp_text = ""
        try:
            resp_text = await llm_handler.chat_completion(messages, response_format={"type": "json_object"})
        except Exception as e:
            logger.error(f"Data Input Error: {e}")

        data = safe_json(resp_text)
        cmd = BackendCommand(command_type="SAVE_DIARY_ENTRY", payload=data).model_dump()
        yield {"type": "commands", "payload": [cmd]}

        history: List[Dict[str, str]] = list(state.get("messages") or [])
        response_text = "Данные сохранены в дневник."
        yield {
            "type": "state_update",
            "response_text": response_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": response_text}],
            "backend_commands": [cmd]
        }

    async def education_node(state: GraphState) -> AsyncGenerator[Dict[str, Any], None]:
        collections = ["stroke_types", "medications", "rehabilitation", "risk_factors"]
        docs = []
        scores = []
        user_ctx = state.get("user_context", UserContext())
        subtype = user_ctx.stroke_subtype if user_ctx else None

        for coll in collections:
            try:
                res = await rag_service.search(coll, state["user_message"], stroke_subtype=subtype)
                docs.extend(res)
                scores.extend([d["score"] for d in res])
            except Exception:
                pass

        rag_conf = max(scores) if scores else 0.0

        if rag_conf < 0.65:
            fallback_text = "К сожалению, точной информации не найдено. Вот общая памятка."
            buttons = [Button(label="Общая памятка", payload={"action": "guide"}).model_dump()]
            yield {"type": "buttons", "payload": buttons}
            yield {"type": "token", "content": fallback_text}
            yield {
                "type": "state_update",
                "response_text": fallback_text,
                "response_type": ResponseType.text_with_buttons,
                "buttons": buttons,
                "backend_commands": []
            }
            return

        context = "\n\n".join([d["content"] for d in docs[:5]])
        patient_ctx = _build_patient_context_str(state.get("user_context"))
        sys_prompt = f"{EDUCATION_SYSTEM_PROMPT}\nКонтекст: {context}{patient_ctx}"
        history: List[Dict[str, str]] = list(state.get("messages") or [])
        messages = [{"role": "system", "content": sys_prompt}] + history
        full_text = ""
        try:
            async for token in llm_handler.chat_completion_stream(messages):
                full_text += token
                yield {"type": "token", "content": token}
        except Exception as e:
            logger.error(f"Education Stream Error: {e}")
            full_text = "Произошла ошибка при генерации ответа."

        yield {
            "type": "state_update",
            "response_text": full_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": full_text}],
            "backend_commands": []
        }

    async def emotional_node(state: GraphState) -> AsyncGenerator[Dict[str, Any], None]:
        patient_ctx = _build_patient_context_str(state.get("user_context"))
        system_prompt = EMOTIONAL_SYSTEM_PROMPT + patient_ctx
        history: List[Dict[str, str]] = list(state.get("messages") or [])
        messages = [{"role": "system", "content": system_prompt}] + history
        full_text = ""
        try:
            async for token in llm_handler.chat_completion_stream(messages):
                full_text += token
                yield {"type": "token", "content": token}
        except Exception as e:
            logger.error(f"Emotional Stream Error: {e}")
            full_text = "Я здесь, чтобы выслушать вас."

        yield {
            "type": "state_update",
            "response_text": full_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": full_text}],
            "backend_commands": []
        }

    async def reminder_node(state: GraphState) -> AsyncGenerator[Dict[str, Any], None]:
        patient_ctx = _build_patient_context_str(state.get("user_context"))
        system_prompt = REMINDER_SYSTEM_PROMPT + patient_ctx
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_message"]}
        ]
        resp_text = ""
        try:
            resp_text = await llm_handler.chat_completion(messages, response_format={"type": "json_object"})
        except Exception as e:
            logger.error(f"Reminder Error: {e}")

        data = safe_json(resp_text)
        cmd = BackendCommand(command_type="UPSERT_REMINDER", payload=data).model_dump()
        yield {"type": "commands", "payload": [cmd]}

        history: List[Dict[str, str]] = list(state.get("messages") or [])
        response_text = "Напоминание сохранено."
        yield {
            "type": "state_update",
            "response_text": response_text,
            "response_type": ResponseType.text,
            "messages": history + [{"role": "assistant", "content": response_text}],
            "backend_commands": [cmd]
        }

    async def off_topic_node(state: GraphState) -> Dict[str, Any]:
        response_text = "Я здесь, чтобы помочь вам с вопросами по инсульту, реабилитации и самочувствию. Спросите меня о лекарствах, давлении или как получить поддержку."
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
        symptoms = state.get("symptom_entities")
        if symptoms and symptoms.symptoms:
            return "red_flag_node"
        return "education_node"

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
        "education_node": "education_node"
    })

    workflow.add_edge("red_flag_node", END)
    workflow.add_edge("data_input_node", END)
    workflow.add_edge("education_node", END)
    workflow.add_edge("emotional_node", END)
    workflow.add_edge("reminder_node", END)
    workflow.add_edge("off_topic_node", END)

    return workflow.compile(checkpointer=MemorySaver())


async def run_graph(input_data: Dict[str, Any], config: Dict[str, Any], *, graph) -> AsyncGenerator[Dict, None]:
    async for event in graph.astream(input_data, config, stream_mode="custom"):
        if event.get("type") != "state_update":
            yield event
    yield {"type": "done"}