"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aegis.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup: create DB tables if they don't exist (handled by Alembic in prod)
    from aegis.database import engine, Base  # noqa: F401 — ensure models registered
    import aegis.models  # noqa: F401 — register all ORM models
    yield
    # Shutdown: close DB engine
    await engine.dispose()


app = FastAPI(
    title="AEGIS - AI Agentic Security Hardening",
    description="AI-driven security hardening for HPE Private Cloud solutions (PCE, PCAI).",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register API routers ---
from aegis.api.v1 import auth, users, workspaces, policies, solution_types, blueprints, instances  # noqa: E402
from aegis.api.v1 import websockets as ws_router  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(solution_types.router, prefix="/api/v1")
app.include_router(blueprints.router, prefix="/api/v1")
app.include_router(instances.router, prefix="/api/v1")
app.include_router(ws_router.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
