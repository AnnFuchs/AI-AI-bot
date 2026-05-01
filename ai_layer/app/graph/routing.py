import logging
from app.schemas import GraphState, IntentEnum

logger = logging.getLogger(__name__)


def route_entry(state: GraphState) -> str:
    if (
        state.get("clarification_pending")
        or (state.get("clarification_step") or 0) > 0
        or state.get("clarification_question")
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
        IntentEnum.off_topic: "off_topic_node",
    }
    return mapping.get(intent, "off_topic_node")

def route_after_wellbeing(state: GraphState) -> str:
    if state.get("clarification_pending"):
        return "clarification_node"
    red_flags = state.get("red_flags") or []
    if any(f.level in ("emergency", "urgent") for f in red_flags):
        return "__end__"
    if state.get("fast_checked"):
        return "__end__"   #уже триажировали — просто завершаем
    return "education_node"