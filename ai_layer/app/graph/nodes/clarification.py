import logging
from typing import Dict, Any, List

from langgraph.config import get_stream_writer

from app.schemas import (
    GraphState, ResponseType, SymptomsData, SymptomEntity,
    RedFlagAlert, ClarificationTriageState, TriageQAPair,
    ClarificationResponse, ClarificationConclusion,
)
from app.prompts import CLARIFICATION_SYSTEM_PROMPT, CLARIFICATION_RESPONSE_PROMPT
from app.llm import LLMHandler
from app.rules import evaluate_red_flags, STROKE_SYMPTOMS
from app.graph.helpers import _get_user_context, _expand_short_answer

logger = logging.getLogger(__name__)


async def clarification_node(state: GraphState, llm_handler: LLMHandler) -> Dict[str, Any]:
    write = get_stream_writer()
    history: List[Dict[str, str]] = list(state.get("messages") or [])

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

    triage_state.symptoms = symptoms_summary
    triage_state.questions_asked = questions_asked

    last_question = state.get("clarification_question") or ""
    last_patient_answer = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"), ""
    )

    if last_question and last_patient_answer:
        already_recorded = any(qa.question == last_question for qa in triage_state.qa_pairs)
        if not already_recorded:
            expanded = await _expand_short_answer(last_question, last_patient_answer, llm_handler)
            triage_state.qa_pairs.append(TriageQAPair(
                question=last_question,
                answer=last_patient_answer,
                expanded=expanded,
            ))

    qa_summary = ""
    if triage_state.qa_pairs:
        qa_summary = "\n".join(
            f"- Вопрос: {qa.question}\n  Ответ: {qa.expanded or qa.answer}"
            for qa in triage_state.qa_pairs
        )
    else:
        qa_summary = "Вопросов ещё не задавалось."

    symptoms_summary = ", ".join(
        f"{k} (сторона: {v.get('side', 'не указана')})"
        for k, v in triage_state.symptoms.items()
    )

    context_text = f"""
    Симптомы пациента: {symptoms_summary}
    Задано вопросов: {triage_state.questions_asked}

    История уточняющего диалога:
    {qa_summary}
    """

    triage_messages = [
        {"role": "system", "content": CLARIFICATION_SYSTEM_PROMPT + context_text},
        {"role": "user", "content": "Задай следующий вопрос или завери триаж."},
    ]
    try:
        result = await llm_handler.complete_structured(triage_messages, ClarificationResponse)
        logger.info(f"Clarification raw result: {result.model_dump()}")
    except Exception as e:
        logger.error(f"Clarification failed: {e} — forcing done")
        result = ClarificationResponse(
            action="done",
            conclusion=ClarificationConclusion(
                is_emergency=False,
                fast_positive=False,
                is_new=None,
                relief_on_movement=None,
                reasoning="Недостаточно данных — рекомендуем обратиться к врачу.",
            ),
        )
    if result.action == "ask" and result.question:
        cleaned = result.question.split("\n")[0].split("(")[0].split("{")[0].split('"')[0].strip()
        cleaned = cleaned.rstrip("?,").rstrip() + "?"
        result.question = cleaned
    if result.action == "done" or questions_asked >= 3:
        conclusion = result.conclusion
        is_emergency = conclusion.is_emergency if conclusion else False
        fast_positive = conclusion.fast_positive if conclusion else False
        is_new = conclusion.is_new if conclusion else None
        relief_on_movement = conclusion.relief_on_movement if conclusion else None
        reasoning = conclusion.reasoning if conclusion and conclusion.reasoning else ""

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
                None,
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
            response_text = await llm_handler.complete(
                [{"role": "user", "content": response_prompt}],
                use_slow_client=True,
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

    question = result.question or "Расскажите подробнее о своих симптомах."
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