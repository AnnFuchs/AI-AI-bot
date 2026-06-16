from app.schemas import SymptomsData, SymptomEntity, BloodPressureReading
from app.rules import evaluate_red_flags


def test_no_flags():
    data = SymptomsData()
    flags = evaluate_red_flags(data)
    assert len(flags) == 0


def test_fast_emergency():
    data = SymptomsData(
        symptoms={
            "face_asymmetry": SymptomEntity(present=True, is_new=True),
            "arm_or_leg_weakness": SymptomEntity(present=True, is_new=True),
        }
    )
    flags = evaluate_red_flags(data, fast_checked=True)
    assert len(flags) > 0
    assert any(f.level == "emergency" for f in flags)
    assert any(
        f.name in ("face_asymmetry", "arm_or_leg_weakness") for f in flags
    )


def test_high_bp_urgent():
    data = SymptomsData(
        blood_pressure=BloodPressureReading(systolic=150.0, diastolic=95.0),
        age_category="45-65"
    )
    flags = evaluate_red_flags(data)
    assert any(f.level == "urgent" for f in flags)


def test_hypertensive_crisis_emergency():
    data = SymptomsData(
        blood_pressure=BloodPressureReading(systolic=190.0, diastolic=125.0)
    )
    flags = evaluate_red_flags(data)
    assert any(
        f.level == "emergency"
        and f.name == "hypertensive_crisis" for f in flags
    )


def test_suicidality_flag():
    data = SymptomsData(
        symptoms={
            "depression": SymptomEntity(present=True, has_suicidality=True)
        }
    )
    flags = evaluate_red_flags(data)
    assert any(
        f.name == "suicidality" and f.level == "emergency" for f in flags
    )


def test_stroke_symptom_not_flagged_without_significance():
    data = SymptomsData(
        symptoms={
            "numbness": SymptomEntity(
                present=True, is_new=False, is_worsening=False
            )
        }
    )
    flags = evaluate_red_flags(data)
    assert not any(f.level == "emergency" for f in flags)
