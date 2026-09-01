from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, field_validator
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
    present: bool = Field(False, description="True если симптом активен прямо сейчас")
    intensity: Optional[int] = Field(None, description="Интенсивность от 1 до 10, null если не указана")
    side: Optional[str] = Field(None, description="Сторона: left / right / both / null")
    value: Optional[float] = Field(None, description="Числовое значение если применимо, иначе null")
    is_new: Optional[bool] = Field(None, description="True если симптом появился впервые сегодня, false если хронический или давний, null если неясно")
    is_worsening: Optional[bool] = Field(None, description="True если симптом усилился, false если стабильный, null если неясно")
    has_suicidality: bool = Field(False, description="True только для симптома depression если есть суицидальные мысли")
    resolved: bool = Field(False, description="True если симптом прошёл или пациент сказал что стало лучше")

    @field_validator('present', 'has_suicidality', 'resolved', mode='before')
    @classmethod
    def none_to_false(cls, v: Any) -> bool:
        return v if v is not None else False


class BloodPressureReading(BaseModel):
    systolic: Optional[float] = Field(None, description="Систолическое давление в мм рт ст")
    diastolic: Optional[float] = Field(None, description="Диастолическое давление в мм рт ст")
    pulse: Optional[int] = Field(None, description="Пульс в ударах в минуту")


class MedicationTaken(BaseModel):
    med_name: str = Field(description="Название препарата")
    dose: Optional[str] = Field(None, description="Доза если указана")
    taken: bool = Field(True, description="True если пациент сообщил что принял препарат")
    scheduled_time: Optional[str] = Field(None, description="Запланированное время приёма если упомянуто")
    note: Optional[str] = Field(None, description="Дополнительная заметка")


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
    href: str


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


# ── LLM Response Models ───────────────────────────────────────────────────────
# Pydantic-схемы для complete_structured() — заменяют safe_json() + json_object

class ClassifierResponse(BaseModel):
    model_config = {"json_schema_extra": {"description": "Классификация интента сообщения пользователя"}}
    intent: IntentEnum = Field(description="Интент: wellbeing_check / data_input / education / emotional_support / reminder_management / social_navigation / off_topic")
    confidence: float = Field(1.0, description="Уверенность классификации от 0.0 до 1.0")

class DataInputResponse(BaseModel):
    """Извлечение замеров здоровья из текста"""
    model_config = {"coerce_numbers_to_str": True}
    systolic_bp: Optional[str] = Field(None, description="Верхнее давление")
    diastolic_bp: Optional[str] = Field(None, description="Нижнее давление")
    pulse: Optional[str] = Field(None, description="Пульс, только цифры")
    blood_sugar: Optional[str] = Field(
        None,
        description="Сахар крови. Если в тексте '10,0', извлеки как '10.0' (через точку)."
    )

class ClarificationConclusion(BaseModel):
    fast_positive: bool = Field(description="True если FAST положительный — лицо и рука/нога на одной стороне поражены одновременно")
    is_new: Optional[bool] = Field(None, description="True если симптом новый сегодня, false если хронический, null если неясно")
    relief_on_movement: Optional[bool] = Field(None, description="True если симптом проходит при движении или массаже")
    is_emergency: bool = Field(description="True если требуется немедленная медицинская помощь")
    reasoning: Optional[str] = Field(None, description="Краткое объяснение решения на русском")

class ClarificationResponse(BaseModel):
    model_config = {"json_schema_extra": {"description": "Решение триажа: задать вопрос или завершить"}}
    action: str = Field(description="ask — задать следующий вопрос пациенту, done — завершить триаж")
    question: Optional[str] = Field(
        None,
        description="Один короткий вопрос на русском языке для пациента. Заканчивается одним знаком вопроса. Без скобок, пояснений, технических терминов и лишних символов."
    )
    conclusion: Optional[ClarificationConclusion] = Field(None, description="Заключение триажа если action=done")


class ReminderResponse(BaseModel):
    model_config = {"json_schema_extra": {"description": "Параметры напоминания извлечённые из сообщения пациента"}}
    action: str = Field(description="Действие: create / update / delete")
    reminder_type: str = Field(description="Тип напоминания: medication / appointment / exercise / measurement")
    med_name: Optional[str] = Field(None, description="Название препарата если применимо")
    time: Optional[str] = Field(None, description="Время в формате ЧЧ:ММ если указано")
    days: Optional[List[str]] = Field(None, description="Дни недели: Mon/Tue/Wed/Thu/Fri/Sat/Sun или daily")
    reminder_id: Optional[str] = Field(None, description="ID напоминания только для update/delete")

class ExtractedSymptoms(BaseModel):
    arm_or_leg_weakness: Optional[SymptomEntity] = Field(None, description="Слабость в руке или ноге")
    face_asymmetry: Optional[SymptomEntity] = Field(None, description="Асимметрия лица, перекос, опущение угла рта")
    balance_loss: Optional[SymptomEntity] = Field(None, description="Нарушение равновесия, шаткость походки")
    numbness: Optional[SymptomEntity] = Field(None, description="Онемение или покалывание в конечностях или лице")
    vision_changes: Optional[SymptomEntity] = Field(None, description="Нарушения зрения: двоение, потеря поля зрения")
    dysphagia: Optional[SymptomEntity] = Field(None, description="Затруднение глотания")
    confusion: Optional[SymptomEntity] = Field(None, description="Спутанность сознания, дезориентация")
    disorientation: Optional[SymptomEntity] = Field(None, description="Дезориентация во времени или пространстве")
    speech_change: Optional[SymptomEntity] = Field(None, description="Нарушение речи: невнятность, афазия, заторможенность")
    headache: Optional[SymptomEntity] = Field(None, description="Головная боль")
    depression: Optional[SymptomEntity] = Field(None, description="Подавленность, депрессия, апатия")
    suicidality: Optional[SymptomEntity] = Field(None, description="Суицидальные мысли или намерения")
    weight_loss: Optional[SymptomEntity] = Field(None, description="Непреднамеренная потеря веса")

class WellbeingExtractionResponse(BaseModel):
    model_config = {"json_schema_extra": {"description": "Симптомы и показатели извлечённые из сообщения пациента"}}
    symptoms: ExtractedSymptoms = Field(default_factory=ExtractedSymptoms, description="Симптомы извлечённые из сообщения пациента")
    blood_pressure: Optional[BloodPressureReading] = Field(None, description="Показания артериального давления если упомянуты")
    medications_taken: List[MedicationTaken] = Field(default_factory=list, description="Препараты которые пациент сообщил что принял")