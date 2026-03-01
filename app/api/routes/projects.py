from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.db import Channel, Pattern, Project, Step
from app.models.schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectSave,
    ProjectSummary,
)
from app.plugins.registry import PluginRegistry

router = APIRouter(tags=["projects"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _load_options():
    """Eager-load the full project tree in one query."""
    return selectinload(Project.patterns).selectinload(Pattern.channels).selectinload(Channel.steps)


async def _get_project_or_404(project_id: int, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).options(_load_options()).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _build_default_pattern(plugin_id: str, steps_per_pattern: int) -> Pattern:
    """Create a default Pattern seeded with plugin channels and empty steps."""
    plugin = PluginRegistry.get(plugin_id)
    channel_defs = plugin.default_channels if plugin else []

    pattern = Pattern(name="Pattern 1", order_index=0)
    for ch_def in channel_defs:
        channel = Channel(
            name=ch_def.name,
            waveform_type=ch_def.waveform_type,
            volume=ch_def.volume,
            pan=ch_def.pan,
            muted=False,
            locked_ranges=[],
        )
        channel.steps = [
            Step(step_index=i, active=False, pitch=ch_def.default_pitch, velocity=100)
            for i in range(steps_per_pattern)
        ]
        pattern.channels.append(channel)
    return pattern


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/projects", response_model=list[ProjectSummary])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    return result.scalars().all()


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    loop_end = payload.loop_end if payload.loop_end >= 0 else payload.steps_per_pattern - 1
    project = Project(
        name=payload.name,
        plugin_id=payload.plugin_id,
        bpm=payload.bpm,
        steps_per_pattern=payload.steps_per_pattern,
        loop_start=payload.loop_start,
        loop_end=loop_end,
    )
    project.patterns.append(_build_default_pattern(payload.plugin_id, payload.steps_per_pattern))
    db.add(project)
    await db.commit()
    await db.refresh(project)
    # Re-fetch with eager loads
    return await _get_project_or_404(project.id, db)


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_project_or_404(project_id, db)


@router.put("/projects/{project_id}", response_model=ProjectRead)
async def save_project(project_id: int, payload: ProjectSave, db: AsyncSession = Depends(get_db)):
    """
    Full project save. Replaces all patterns/channels/steps with the
    state sent from the frontend. Simpler than partial-patch for v1.
    """
    project = await _get_project_or_404(project_id, db)

    project.name = payload.name
    project.bpm = payload.bpm
    project.steps_per_pattern = payload.steps_per_pattern
    project.loop_start = payload.loop_start
    project.loop_end = payload.loop_end

    # Wipe existing patterns (cascade deletes channels + steps)
    project.patterns.clear()

    for pat_data in payload.patterns:
        pattern = Pattern(name=pat_data.name, order_index=pat_data.order_index)
        for ch_data in pat_data.channels:
            channel = Channel(
                name=ch_data.name,
                waveform_type=ch_data.waveform_type,
                volume=ch_data.volume,
                pan=ch_data.pan,
                muted=ch_data.muted,
                locked_ranges=[r.model_dump() for r in ch_data.locked_ranges],
            )
            channel.steps = [
                Step(
                    step_index=s.step_index,
                    active=s.active,
                    pitch=s.pitch,
                    velocity=s.velocity,
                )
                for s in ch_data.steps
            ]
            pattern.channels.append(channel)
        project.patterns.append(pattern)

    await db.commit()
    return await _get_project_or_404(project_id, db)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await _get_project_or_404(project_id, db)
    await db.delete(project)
    await db.commit()
