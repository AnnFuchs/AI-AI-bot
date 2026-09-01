import logging
from typing import Dict, Any, List

from app.schemas import GraphState, IntentEnum, ClassifierResponse
from app.prompts import CLASSIFIER_SYSTEM_PROMPT
from app.llm import LLMHandler
from app.graph.helpers import _get_user_context, _build_patient_context_str, _should_reset_episode

logger = logging.getLogger(__name__)


async def classifier_node(state: GraphState, llm_handler: LLMHandler) -> Dict[str, Any]:
    user_ctx = _get_user_context(state)
    patient_ctx = _build_patient_context_str(user_ctx)
    history: List[Dict[str, str]] = list(state.get("messages") or [])

    messages = [
        {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT + patient_ctx},
        {"role": "user", "content": state["user_message"]},
    ]

    try:
        result = await llm_handler.complete_structured(messages, ClassifierResponse)
        intent = result.intent
        confidence = result.confidence
        logger.info(f"Classifier: intent={intent} confidence={confidence}")
    except Exception as e:
        logger.error(f"Classifier failed: {type(e).__name__}: {e}")
        intent = IntentEnum.off_topic
        confidence = 0.0

    reset = _should_reset_episode(state, intent)
    if reset:
        logger.info(f"Symptom episode reset: intent switched to {intent}")

    return {
        "intent": intent,
        "intent_confidence": confidence,
        "messages": history + [{"role": "user", "content": state["user_message"]}],
        "accumulated_symptoms": None if reset else state.get("accumulated_symptoms"),
        "symptom_episode_active": False if reset else state.get("symptom_episode_active"),
        "fast_checked": False if reset else state.get("fast_checked"),
        "clarification_pending": False if reset else state.get("clarification_pending"),
    }