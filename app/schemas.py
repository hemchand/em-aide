from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any
import datetime as dt

class Signal(BaseModel):
    name: str
    value: float
    unit: str = "count"

class EntityRef(BaseModel):
    kind: Literal["pr","issue"]
    id: str
    state: str
    age_days: float | None = None
    size: float | None = None
    flags: List[str] = Field(default_factory=list)

class ContextPacketSchema(BaseModel):
    org: str
    team: str
    as_of: dt.datetime
    goals: List[str] = Field(default_factory=list)
    signals: List[Signal]
    entities: List[EntityRef]
    history: Dict[str, Any] = Field(default_factory=dict)

class ActionSchema(BaseModel):
    title: str
    rationale: str
    evidence: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    expected_impact: str
    risk: str
    confidence: float = Field(ge=0.0, le=1.0)

class RiskSchema(BaseModel):
    title: str
    description: str
    severity: Literal["low","medium","high"]
    likelihood: float = Field(ge=0.0, le=1.0)
    signals: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)

class WeeklyPlanSchema(BaseModel):
    week_start: dt.date
    generated_at: dt.datetime
    top_actions: List[ActionSchema]
    top_risks: List[RiskSchema]
    summary: str
