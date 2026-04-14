import pytest
from app.schemas import SymptomsData, SymptomEntity, RedFlag
from app.rules import evaluate_red_flags

def test_no_flags():
    data = SymptomsData()
    flags = evaluate_red_flags(data)
    assert len(flags) == 0

def test_fast_emergency():
    data = SymptomsData(
        symptoms={
            "face_drooping": SymptomEntity(present=True),
            "arm_weakness": SymptomEntity(present=False),
            "speech_disorder": SymptomEntity(present=False)
        }
    )
    flags = evaluate_red_flags(data)
    assert len(flags) > 0
    assert flags[0].level == "emergency"
    assert "FAST" in flags[0].name

def test_high_bp_urgent():
    data = SymptomsData(
        symptoms={
            "blood_pressure_high": SymptomEntity(present=True, value=190.0)
        }
    )
    flags = evaluate_red_flags(data)
    assert any(f.level == "urgent" for f in flags)
