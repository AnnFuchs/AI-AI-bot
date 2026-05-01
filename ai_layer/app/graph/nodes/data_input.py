import logging
from typing import Dict, Any, List

from langgraph.config import get_stream_writer

from app.schemas import (
    GraphState, ResponseType, SymptomsData,
    RedFlagAlert, BackendCommand, DataInputResponse,
)
from app.prompts import DATA_INPUT_SYSTEM_PROMPT
from app.llm import LLMHandler
from app.rules import evaluate_red_flags
from app.graph.helpers import _get_user_context

logger = logging.getLogger(__name__)


async def data_input_node(state: GraphState, llm_handler: LLMHandler) -> Dict[str, Any]:
    write = get_stream_writer()
    DATA_INPUT_FEW_SHOT = [
        {"role": "user", "content": "Сахар 10.0"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "chat_1",
                "type": "function",
                "function": {
                    "name": "DataInputResponse",
                    "arguments": '{"blood_sugar": "10.0"}'
                }
            }]
        },
        {"role": "user", "content": "130/85, пульс 70"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "chat_2",
                "type": "function",
                "function": {
                    "name": "DataInputResponse",
                    "arguments": '{"systolic_bp": "130", "diastolic_bp": "85", "pulse": "70"}'
                }
            }]
        }
    ]
    messages = [
        {"role": "system", "content": DATA_INPUT_SYSTEM_PROMPT},
        *DATA_INPUT_FEW_SHOT,  # Распаковываем примеры здесь
        {"role": "user", "content": state["user_message"]},
    ]

    try:
        result = await llm_handler.complete_structured(messages, DataInputResponse, method="json_mode")
        logger.info(f"Data input extracted: {result.model_dump()}")
    except Exception as e:
        logger.error(f"Data input extraction failed: {type(e).__name__}: {e}", exc_info=True)
        result = DataInputResponse()

    user_id = state.get("user_id")
    commands = []
    history: List[Dict[str, str]] = list(state.get("messages") or [])

    if result.systolic_bp or result.diastolic_bp:
        commands.append(BackendCommand(
            command_type="SAVE_DIARY_ENTRY",
            payload={
                "user_id": user_id,
                "entry_type": "blood_pressure",
                "entry_json": {
                    "systolic": result.systolic_bp,
                    "diastolic": result.diastolic_bp,
                    "pulse": result.pulse,
                },
            },
        ).model_dump())

    if result.blood_sugar is not None:
        commands.append(BackendCommand(
            command_type="SAVE_DIARY_ENTRY",
            payload={
                "user_id": user_id,
                "entry_type": "blood_test",
                "entry_json": {
                    "blood_sugar": result.blood_sugar,
                    "user_message_raw": state["user_message"],
                },
            },
        ).model_dump())

    bp_symptoms = SymptomsData(
        blood_pressure={
            "systolic": result.systolic_bp,
            "diastolic": result.diastolic_bp,
            "pulse": result.pulse,
        }
    )
    user_ctx = _get_user_context(state)
    if user_ctx:
        bp_symptoms.age_category = user_ctx.age_category

    flags = evaluate_red_flags(bp_symptoms)
    has_emergency = any(f.level == "emergency" for f in flags)
    has_urgent = any(f.level == "urgent" for f in flags)

    if has_emergency:
        alert = RedFlagAlert(red_flags=flags, message="⚠️ Позвоните 112 немедленно!")
        commands.append(BackendCommand(command_type="ALERT_DOCTOR", payload=alert.model_dump()).model_dump())
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