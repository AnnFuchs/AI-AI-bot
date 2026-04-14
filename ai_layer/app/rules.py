from typing import List
from app.schemas import SymptomsData, RedFlag, SymptomEntity

RED_FLAG_RULES = [
    # (name, predicate, level)
    ("FAST_symptoms", lambda s: _check_symptom(s, 'face_drooping') or _check_symptom(s, 'arm_weakness') or _check_symptom(s, 'speech_disorder'), "emergency"),
    ("vision_loss", lambda s: _check_symptom(s, 'vision_loss'), "emergency"),
    ("loss_of_consciousness", lambda s: _check_symptom(s, 'loss_of_consciousness'), "emergency"),
    ("severe_headache", lambda s: _check_symptom(s, 'headache') and _get_intensity(s, 'headache') >= 8, "emergency"),
    ("high_bp_critical", lambda s: _check_symptom(s, 'blood_pressure_high') and _get_value(s, 'blood_pressure_high') >= 180, "urgent"),
    ("general_poor", lambda s: s.general_wellbeing == 'poor', "warning"),
]

def _check_symptom(s: SymptomsData, name: str) -> bool:
    sym = s.symptoms.get(name, SymptomEntity())
    return sym.present

def _get_intensity(s: SymptomsData, name: str) -> float:
    sym = s.symptoms.get(name, SymptomEntity())
    return sym.intensity or 0

def _get_value(s: SymptomsData, name: str) -> float:
    sym = s.symptoms.get(name, SymptomEntity())
    return sym.value or 0

def evaluate_red_flags(symptoms: SymptomsData) -> List[RedFlag]:
    flags = []
    for name, predicate, level in RED_FLAG_RULES:
        try:
            if predicate(symptoms):
                flags.append(RedFlag(name=name, level=level, description=f"Выявлен тревожный симптом: {name}"))
        except Exception:
            continue
    return flags
