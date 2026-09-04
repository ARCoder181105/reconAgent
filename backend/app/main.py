"""FastAPI application entrypoint (Iteration 07).

Mounts the routers and initializes the DB schema. Run with:

    make dev          # uvicorn backend.app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.app.db import init_db
from backend.app.events import event_stream
from backend.app.routers import data, exceptions, inspector, report, score
from backend.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ReconAgent",
    description="Multi-source fuzzy reconciliation engine (Razorpay buildathon).",
    version="0.7.0",
    lifespan=lifespan,
)

# CORS: allow the Vite frontend (dev + preview) to call the API. Origin list is
# env-configurable via CORS_ORIGINS (comma-separated).
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(report.router)
app.include_router(exceptions.router)
app.include_router(inspector.router)
app.include_router(score.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/events")
async def sse_events():
    """Server-Sent Events stream — the browser opens this once and stays
    connected.  Every mutation (run-reconciliation, resolve, approve) pushes
    a lightweight event that triggers client-side re-fetches."""
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
