"""FastAPI entrypoint for the VisualSprint API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from visualsprint_api.config import settings
from visualsprint_api.routes.actions import router as actions_router
from visualsprint_api.routes.agents import router as agents_router
from visualsprint_api.routes.capture import router as capture_router
from visualsprint_api.routes.dev import router as dev_router
from visualsprint_api.routes.health import router as health_router
from visualsprint_api.routes.insights import router as insights_router
from visualsprint_api.routes.knowledge import router as knowledge_router
from visualsprint_api.routes.memory import router as memory_router
from visualsprint_api.routes.meta import router as meta_router
from visualsprint_api.routes.meetings import router as meetings_router
from visualsprint_api.routes.outputs import router as outputs_router


app = FastAPI(
    title="VisualSprint API",
    version=settings.version,
    summary="Deterministic control-plane shell for the VisualSprint platform.",
)

if settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health_router, prefix="/api")
if settings.demo_seed_enabled:
    app.include_router(dev_router, prefix="/api")
app.include_router(meta_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(meetings_router, prefix="/api")
app.include_router(capture_router, prefix="/api")
app.include_router(insights_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(outputs_router, prefix="/api")
app.include_router(actions_router, prefix="/api")


@app.get("/")
def get_root() -> dict[str, str]:
    return {
        "name": "VisualSprint API",
        "message": "Deterministic platform services are online.",
    }
