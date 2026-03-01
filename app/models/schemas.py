from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ─── Step ────────────────────────────────────────────────────────────────────

class StepSchema(BaseModel):
    step_index: int
    active: bool = False
    pitch: int = 60
    velocity: int = 100


class StepRead(StepSchema):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ─── LockedRange ──────────────────────────────────────────────────────────────

class LockedRange(BaseModel):
    start: int
    end: int


# ─── Channel ─────────────────────────────────────────────────────────────────

class ChannelBase(BaseModel):
    name: str
    waveform_type: str = "square"
    volume: float = Field(default=0.8, ge=0.0, le=1.0)
    pan: float = Field(default=0.0, ge=-1.0, le=1.0)
    muted: bool = False
    locked_ranges: list[LockedRange] = []


class ChannelCreate(ChannelBase):
    steps: list[StepSchema] = []


class ChannelRead(ChannelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    steps: list[StepRead] = []


# ─── Pattern ─────────────────────────────────────────────────────────────────

class PatternBase(BaseModel):
    name: str = "Pattern 1"
    order_index: int = 0


class PatternCreate(PatternBase):
    channels: list[ChannelCreate] = []


class PatternRead(PatternBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    channels: list[ChannelRead] = []


# ─── Project ─────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    plugin_id: str
    bpm: int = Field(default=120, ge=20, le=300)
    steps_per_pattern: int = Field(default=16, ge=4, le=256)
    loop_start: int = 0
    loop_end: int = Field(default=-1)   # -1 means "set to steps_per_pattern - 1"


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    plugin_id: str
    bpm: int
    steps_per_pattern: int
    loop_start: int
    loop_end: int
    updated_at: datetime


class ProjectRead(ProjectSummary):
    created_at: datetime
    patterns: list[PatternRead] = []


class ProjectSave(BaseModel):
    """Full project state sent from the frontend on save."""
    name: str
    bpm: int = Field(ge=20, le=300)
    steps_per_pattern: int = Field(ge=4, le=256)
    loop_start: int = 0
    loop_end: int = 0
    patterns: list[PatternCreate] = []
