from fastapi import APIRouter
from app.plugins.registry import PluginRegistry

router = APIRouter(tags=["plugins"])


@router.get("/plugins")
async def list_plugins() -> list[dict]:
    """Return all registered synthesizer plugins."""
    return [p.to_dict() for p in PluginRegistry.list_all()]
