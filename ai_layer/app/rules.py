from typing import List, Optional
from app.schemas import SymptomsData, RedFlag

STROKE_SYMPTOMS = {
    "arm_or_leg_weakness",
    "face_asymmetry",
    "balance_loss",
    "numbness",
    "vision_changes",
    "dysphagia",
    "confusion",
    "disorientation",
    "speech_change",
}

STROKE_SYMPTOM_DESCRIPTIONS = {
    "arm_or_leg_weakness": "Слабость в руке или ноге",
    "face_asymmetry": "Асимметрия лица",
    "balance_loss": "Нарушение равновесия",
    "numbness": "Онемение",
    "vision_changes": "Нарушение зрения",
    "dysphagia": "Нарушение глотания",
    "confusion": "Спутанность сознания",
    "disorientation": "Дезориентация",
    "speech_change": "Нарушение речи",
}


def _get_bp_thresholds(symptoms: SymptomsData):
    age_category = symptoms.age_category or "45-65"
    if age_category == "65+":
        return 140, 90
    return 130, 80


def evaluate_red_flags(
    symptoms: Optional[SymptomsData],
    known_symptoms: Optional[List[str]] = None,
    stroke_date: Optional[str] = None,
    fast_checked: bool = False,
) -> List[RedFlag]:
    if not symptoms:
        return []

    flags: List[RedFlag] = []
    known = set(known_symptoms or [])

    # --- Stroke symptoms ---
    present_stroke_count = sum(
        1 for k, e in symptoms.symptoms.items()
        if k in STROKE_SYMPTOMS and e.present
    )

    for sym_key in STROKE_SYMPTOMS:
        entity = symptoms.symptoms.get(sym_key)
        if not entity or not entity.present:
            continue

        is_known_chronic = sym_key in known and stroke_date

        is_significant = (
            entity.is_new is True
            or entity.is_worsening is True
            # после clarification: emergency только если ≥2 инсультных симптомов
            # (изолированное онемение без подтверждения FAST — не emergency)
            or (fast_checked and entity.is_new is not False and present_stroke_count >= 2)
        )

        if not is_significant:
            continue

        if is_known_chronic:
            flags.append(RedFlag(
                name=sym_key,
                level="warning",
                description=STROKE_SYMPTOM_DESCRIPTIONS[sym_key],
                target_info="Хронический постинсультный симптом — сообщите врачу при ухудшении"
            ))
        else:
            flags.append(RedFlag(
                name=sym_key,
                level="emergency",
                description=STROKE_SYMPTOM_DESCRIPTIONS[sym_key],
                target_info="Возможный инсульт — немедленно вызовите скорую"
            ))
    # --- Headache ---
    headache = symptoms.symptoms.get("headache")
    if headache and headache.present:
        is_thunderclap = headache.is_new and (headache.intensity or 0) >= 8
        if is_thunderclap or headache.is_worsening:
            flags.append(RedFlag(
                name="headache",
                level="emergency",
                description="Внезапная сильная головная боль",
                target_info="Возможное субарахноидальное кровоизлияние"
            ))

    # --- Suicidality ---
    depression = symptoms.symptoms.get("depression")
    suicidality = symptoms.symptoms.get("suicidality")
    if (depression and depression.present and depression.has_suicidality) or \
            (suicidality and suicidality.present):
        flags.append(RedFlag(
            name="suicidality",
            level="emergency",
            description="Мысли о самоповреждении или суициде",
            target_info="Кризисная линия: 8-800-2000-122"
        ))

    # --- Blood pressure ---
    bp = symptoms.blood_pressure
    if bp:
        sys_red = 180
        dia_red = 120
        sys_target, dia_target = _get_bp_thresholds(symptoms)

        if (bp.systolic and bp.systolic >= sys_red) or \
                (bp.diastolic and bp.diastolic >= dia_red):
            flags.append(RedFlag(
                name="hypertensive_crisis",
                level="emergency",
                description=f"Гипертонический криз: {bp.systolic}/{bp.diastolic} мм рт.ст.",
                target_info="Немедленно вызовите скорую"
            ))
        elif (bp.systolic and bp.systolic > sys_target) or \
                (bp.diastolic and bp.diastolic > dia_target):
            flags.append(RedFlag(
                name="elevated_bp",
                level="urgent",
                description=f"Давление выше целевого: {bp.systolic}/{bp.diastolic} мм рт.ст.",
                target_info=f"Целевое: {sys_target}/{dia_target} мм рт.ст."
            ))

    # --- Weight loss ---
    weight_loss = symptoms.symptoms.get("weight_loss")
    if weight_loss and weight_loss.present:
        flags.append(RedFlag(
            name="weight_loss",
            level="warning",
            description="Снижение веса",
            target_info="Обсудите с врачом на ближайшем приёме"
        ))

    return flags