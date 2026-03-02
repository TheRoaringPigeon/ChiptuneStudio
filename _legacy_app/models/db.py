from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plugin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    bpm: Mapped[int] = mapped_column(Integer, default=120)
    steps_per_pattern: Mapped[int] = mapped_column(Integer, default=16)
    loop_start: Mapped[int] = mapped_column(Integer, default=0)
    loop_end: Mapped[int] = mapped_column(Integer, default=15)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    patterns: Mapped[list["Pattern"]] = relationship(
        "Pattern", back_populates="project", cascade="all, delete-orphan", order_by="Pattern.order_index"
    )


class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="Pattern 1")
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped["Project"] = relationship("Project", back_populates="patterns")
    channels: Mapped[list["Channel"]] = relationship(
        "Channel", back_populates="pattern", cascade="all, delete-orphan", order_by="Channel.id"
    )


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pattern_id: Mapped[int] = mapped_column(Integer, ForeignKey("patterns.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    waveform_type: Mapped[str] = mapped_column(String(32), default="square")
    volume: Mapped[float] = mapped_column(Float, default=0.8)
    pan: Mapped[float] = mapped_column(Float, default=0.0)
    muted: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_ranges: Mapped[list] = mapped_column(JSON, default=list)
    synth_params: Mapped[dict] = mapped_column(JSON, default=dict)

    pattern: Mapped["Pattern"] = relationship("Pattern", back_populates="channels")
    steps: Mapped[list["Step"]] = relationship(
        "Step", back_populates="channel", cascade="all, delete-orphan", order_by="Step.step_index"
    )


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    pitch: Mapped[int] = mapped_column(Integer, default=60)  # MIDI note
    velocity: Mapped[int] = mapped_column(Integer, default=100)  # 0-127

    channel: Mapped["Channel"] = relationship("Channel", back_populates="steps")
