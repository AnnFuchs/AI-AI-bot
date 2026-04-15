from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel
from typing_extensions import TypedDict


class IntentEnum(str, Enum):
    wellbeing_check = "wellbeing_check"
    data_input = "data_input"
    education = "education"
    emotional_support = "emotional_support"
    reminder_management = "reminder_management"
    social_navigation = "social_navigation"
    off_topic = "off_topic"


class UserContext(BaseModel):
    user_id: str
    role: str = "patient"
    stroke_type: Optional[str] = None
    stroke_toast_subtype: Optional[str] = None
    stroke_hemo_subtype: Optional[str] = None
    medications: List[str] = []
    age_category: Optional[str] = None  # "young" | "middle" | "old_independent" | "old_dependent"
    has_stenosis: Optional[bool] = None
    known_symptoms: List[str] = []     # populated by backend from diary history


class SymptomEntity(BaseModel):
    present: bool = False
    intensity: Optional[int] = None    # 1-10
    side: Optional[str] = None
    value: Optional[float] = None
    is_new: bool = False
    is_worsening: bool = False
    has_suicidality: bool = False      # only for depression key


class BloodPressureReading(BaseModel):
    systolic: Optional[float] = None
    diastolic: Optional[float] = None
    pulse: Optional[int] = None


class MedicationTaken(BaseModel):
    med_name: str
    dose: Optional[str] = None
    taken: bool = True
    scheduled_time: Optional[str] = None
    note: Optional[str] = None


class SymptomsData(BaseModel):
    symptoms: Dict[str, SymptomEntity] = {}
    general_wellbeing: str = "normal"  # "good" | "normal" | "poor"
    free_text: str = ""
    blood_pressure: Optional[BloodPressureReading] = None
    medications_taken: List[MedicationTaken] = []
    # patient context for personalised BP thresholds
    age_category: Optional[str] = None
    has_stenosis: Optional[bool] = None


class RedFlag(BaseModel):
    name: str
    level: str                         # "emergency" | "urgent" | "warning"
    description: str
    target_info: Optional[str] = None


class RedFlagAlert(BaseModel):
    red_flags: List[RedFlag] = []
    message: str


class BackendCommand(BaseModel):
    command_type: str
    payload: Any


class Button(BaseModel):
    label: str
    payload: Dict[str, Any]


class ResponseType(str, Enum):
    text = "text"
    text_with_buttons = "text_with_buttons"
    alert = "alert"


class GraphState(TypedDict, total=False):
    user_message: str
    user_id: str
    session_id: str
    user_context: UserContext
    messages: List[Dict[str, str]]
    intent: Optional[IntentEnum]
    intent_confidence: Optional[float]
    rag_docs: Optional[List[Any]]
    rag_confidence: Optional[float]
    red_flags: Optional[List[RedFlag]]
    symptom_entities: Optional[SymptomsData]
    response_text: Optional[str]
    response_type: Optional[ResponseType]
    buttons: Optional[List[Button]]
    backend_commands: Optional[List[BackendCommand]]
    alert_payload: Optional[RedFlagAlert]


class ReminderCommand(BaseModel):
    action: str
    reminder_type: str
    time: Optional[str] = None
    days: Optional[List[str]] = None
    med_name: Optional[str] = None
    reminder_id: Optional[str] = None