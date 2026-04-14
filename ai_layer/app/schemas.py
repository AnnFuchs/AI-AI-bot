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

class IntentClassification(BaseModel):
    intent: IntentEnum
    confidence: float

class UserContext(BaseModel):
    user_id: str
    role: str = "patient"
    stroke_type: Optional[str] = None
    stroke_subtype: Optional[str] = None
    medications: List[str] = []

class SymptomEntity(BaseModel):
    present: bool = False
    intensity: Optional[int] = None
    side: Optional[str] = None
    value: Optional[float] = None
    type: Optional[str] = None

class SymptomsData(BaseModel):
    symptoms: Dict[str, SymptomEntity] = {}
    general_wellbeing: str = "normal"
    free_text: str = ""

class RedFlag(BaseModel):
    name: str
    level: str
    description: str

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
    messages: List[Dict[str, str]]  # история диалога: [{"role": "user/assistant", "content": "..."}]
    intent: Optional[IntentEnum]
    intent_confidence: Optional[float]
    extracted_data: Optional[Dict]
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