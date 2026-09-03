"""FastAPI application entrypoint (Iteration 07).

Mounts the routers and initializes the DB schema. Run with:

    make dev          # uvicorn backend.app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.db import init_db
from backend.app.routers import data, exceptions, inspector, report, score


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

app.include_router(data.router)
app.include_router(report.router)
app.include_router(exceptions.router)
app.include_router(inspector.router)
app.include_router(score.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
