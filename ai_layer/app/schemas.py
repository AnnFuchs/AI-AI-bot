from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, field_validator
from typing_extensions import TypedDict

class SourceReference(BaseModel):
    source: str      # "Клинические_рекомендации_Ишемический_инсульт_2024.pdf"

class ResponseMeta(BaseModel):
    confidence: float
    confidence_label: str               # "high" | "medium" | "low" | "insufficient"
    sources: List[SourceReference] = []
    intent: str
    used_rag: bool

class IntentEnum(str, Enum):
    wellbeing_check = "wellbeing_check"
    data_input = "data_input"
    education = "education"
    emotional_support = "emotional_support"
    reminder_management = "reminder_management"
    social_navigation = "social_navigation"
    off_topic = "off_topic"


class Medication(BaseModel):
    name: str
    dose_mg: int
    frequency: str


class UserContext(BaseModel):
    user_id: str
    role: str = "patient"
    stroke_date: Optional[str] = None
    stroke_type: Optional[str] = None
    stroke_toast_subtype: Optional[str] = None
    stroke_hemo_subtype: Optional[str] = None
    medications: Optional[List[Medication]] = None # объекты от бэкенда: {name, dose_mg, frequency}
    age_category: Optional[str] = None  # "18-44" | "45-65" | "65+"
    known_symptoms: Optional[List[str]] = []      # populated by backend from diary history
    doctor_id: Optional[str] = None


class SymptomEntity(BaseModel):
    present: bool = False
    intensity: Optional[int] = None
    side: Optional[str] = None
    value: Optional[float] = None
    is_new: Optional[bool] = None
    is_worsening: Optional[bool] = None
    has_suicidality: bool = False
    resolved: bool = False

    @field_validator('present', 'has_suicidality', 'resolved', mode='before')
    @classmethod
    def none_to_false(cls, v: Any) -> bool:
        return v if v is not None else False


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
    age_category: Optional[str] = None  # передаётся из UserContext для BP-порогов


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

class TriageQAPair(BaseModel):
    question: str
    answer: str
    expanded: str

class TriageKnown(BaseModel):
    is_new: Optional[bool] = None
    fast_positive: Optional[bool] = None
    relief_on_movement: Optional[bool] = None

class ClarificationTriageState(BaseModel):
    symptoms: Dict[str, Any] = {}
    qa_pairs: List[TriageQAPair] = []
    known: TriageKnown = TriageKnown()
    questions_asked: int = 0


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
    response_meta: Optional[ResponseMeta]
    # Накопленные симптомы по эпизоду (мерж между турами)
    accumulated_symptoms: Optional[SymptomsData]
    # True пока диалог про самочувствие активен
    symptom_episode_active: Optional[bool]
    # FAST-дискриминаторы уже проверены
    fast_checked: Optional[bool]
    # Pending clarification — бот ждёт ответа на уточняющий вопрос
    clarification_pending: Optional[bool]
    # Последний уточняющий вопрос
    clarification_question: Optional[str]
    clarification_step: Optional[int] = None         # "fast" | "onset" | "relief" | "done"
    fast_negative: Optional[bool]              # True = FAST отрицательный (лицо/нога не затронуты)
    relief_on_movement: Optional[bool]
    clarification_triage_state: Optional[ClarificationTriageState]

class ReminderCommand(BaseModel):
    action: str
    reminder_type: str
    time: Optional[str] = None
    days: Optional[List[str]] = None
    med_name: Optional[str] = None
    reminder_id: Optional[str] = None

