from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.api.routes import plugins as plugins_router
from app.api.routes import projects as projects_router
from app.plugins.registry import PluginRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Discover and register plugins
    PluginRegistry.discover()
    yield
    await engine.dispose()


app = FastAPI(title="ChiptuneStudio", lifespan=lifespan)

app.include_router(plugins_router.router, prefix="/api")
app.include_router(projects_router.router, prefix="/api")

static_dir = Path(__file__).parent.parent / "static"

@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(str(static_dir / "index.html"))

# Mount static assets at /static so HTML refs like /static/js/... resolve correctly
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
