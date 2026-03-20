from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware  # Trigger reload
from contextlib import asynccontextmanager

from backend.database import init_db
from backend.routers import sandbox, storyboard, grimoire, settings, muse, render, memory


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the SQLite WAL DB on startup
    await init_db()
    yield


app = FastAPI(
    title="Genesis Engine MVP",
    description="Backend Monolith for The Grimoire Story Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup for future frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In MVP, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sandbox.router, prefix="/api/v1/sandbox", tags=["Sandbox"])
app.include_router(sandbox.router, prefix="/ws", tags=["WebSocket"])
app.include_router(storyboard.router, prefix="/api/v1/storyboard", tags=["Storyboard"])
app.include_router(grimoire.router, prefix="/api/v1/grimoire", tags=["Grimoire"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(muse.router, prefix="/api/v1/muse", tags=["Muse"])
app.include_router(render.router, prefix="/api/v1/render", tags=["Render"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
