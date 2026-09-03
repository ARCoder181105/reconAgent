"""Application configuration.

Reads environment variables (via .env) for runtime settings that should not
live in code: LLM credentials, data-generator tunables, DB path, scoring weights.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from backend.constants import DEFAULT_GEMINI_MODEL

# Repo root is two levels above this module (backend/config.py -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"


def _env_path() -> Path:
    return REPO_ROOT / ".env"


@dataclass(frozen=True)
class Settings:
    """Typed view over the environment. Values fall back to sane defaults."""

    repo_root: Path = field(default_factory=lambda: REPO_ROOT)

    # LLM (Stage 5)
    gemini_api_key: str = ""
    gemini_model: str = DEFAULT_GEMINI_MODEL

    # Data generator
    seed: int = 42
    batch_size: int = 60

    # Database
    db_path: Path = field(default_factory=lambda: Path("backend/data/recon.sqlite3"))

    # Scoring
    fp_weight: float = 3.0

    # Logging
    log_level: str = "INFO"

    @property
    def resolved_db_path(self) -> Path:
        p = self.db_path
        if not p.is_absolute():
            p = REPO_ROOT / p
        return p

    @property
    def data_dir(self) -> Path:
        return REPO_ROOT / "backend" / "data"


def load_settings() -> Settings:
    """Load .env if present, then build a Settings instance from the environment."""
    load_dotenv(_env_path())
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        seed=int(os.getenv("RECON_SEED", "42")),
        batch_size=int(os.getenv("RECON_BATCH_SIZE", "60")),
        db_path=Path(os.getenv("RECON_DB_PATH", "backend/data/recon.sqlite3")),
        fp_weight=float(os.getenv("RECON_FP_WEIGHT", "3.0")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


settings = load_settings()
