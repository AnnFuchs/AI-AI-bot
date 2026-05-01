import logging
from typing import Dict, Any, AsyncGenerator
from functools import partial

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.schemas import GraphState
from app.llm import LLMHandler
from app.rag import RAGService
from app.graph.nodes import (
    classifier_node, wellbeing_node, clarification_node,
    data_input_node, education_node, emotional_node,
    reminder_node, off_topic_node,
)
from app.graph.routing import route_entry, route_by_intent, route_after_wellbeing

logger = logging.getLogger(__name__)


def build_workflow(llm_handler: LLMHandler, rag_service: RAGService):
    """
    Собирает и компилирует LangGraph граф.
    Ноды получают llm_handler и rag_service через functools.partial —
    это позволяет тестировать каждую ноду отдельно с моком.
    """

    async def entry_router_node(state: GraphState) -> Dict[str, Any]:
        logger.info(
            f"entry_router: clarification_pending={state.get('clarification_pending')}, "
            f"step={state.get('clarification_step')}, "
            f"fast_checked={state.get('fast_checked')}, "  # ← добавь
            f"question={state.get('clarification_question')!r}"
        )
        return {}

    workflow = StateGraph(GraphState)

    # Регистрируем ноды — partial прокидывает зависимости без глобального состояния
    workflow.add_node("entry_router_node", entry_router_node)
    workflow.add_node("classifier_node",     partial(classifier_node,    llm_handler=llm_handler))
    workflow.add_node("wellbeing_node",      partial(wellbeing_node,     llm_handler=llm_handler))
    workflow.add_node("clarification_node",  partial(clarification_node, llm_handler=llm_handler))
    workflow.add_node("data_input_node",     partial(data_input_node,    llm_handler=llm_handler))
    workflow.add_node("education_node",      partial(education_node,     llm_handler=llm_handler, rag_service=rag_service))
    workflow.add_node("emotional_node",      partial(emotional_node,     llm_handler=llm_handler))
    workflow.add_node("reminder_node",       partial(reminder_node,      llm_handler=llm_handler))
    workflow.add_node("off_topic_node",      off_topic_node)

    # Рёбра
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
        "off_topic_node": "off_topic_node",
    })
    workflow.add_conditional_edges("wellbeing_node", route_after_wellbeing, {
        "clarification_node": "clarification_node",
        "education_node": "education_node",
        "__end__": END,
    })
    workflow.add_edge("clarification_node", END)
    workflow.add_edge("data_input_node",    END)
    workflow.add_edge("education_node",     END)
    workflow.add_edge("emotional_node",     END)
    workflow.add_edge("reminder_node",      END)
    workflow.add_edge("off_topic_node",     END)

    return workflow.compile(checkpointer=MemorySaver())


async def run_graph(
    input_data: Dict[str, Any],
    config: Dict[str, Any],
    *,
    graph,
) -> AsyncGenerator[Dict, None]:
    async for event in graph.astream(input_data, config, stream_mode="custom"):
        if isinstance(event, dict):
            yield event