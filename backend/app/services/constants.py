"""services package constants.

Canonical event types used by the maker-checker workflow. Source of truth:
``docs/taxonomy.md``; also mirrored in ``backend/constants.py`` so routers can
refer to the same events without importing the service.
"""
from __future__ import annotations

from backend.constants import (
    EVENT_CHECKER_APPROVED,
    EVENT_CHECKER_REJECTED,
    EVENT_CREATED,
    EVENT_MAKER_PROPOSED,
)

# Re-export with the names the service layer already uses.
EV_CREATED = EVENT_CREATED
EV_MAKER_PROPOSED = EVENT_MAKER_PROPOSED
EV_CHECKER_APPROVED = EVENT_CHECKER_APPROVED
EV_CHECKER_REJECTED = EVENT_CHECKER_REJECTED

# It8: LLM tie-break event (append-only, never auto-close).
EVENT_AI_TIEBREAK_SUGGESTED = "AI_TIEBREAK_SUGGESTED"

EVENT_TYPES = (
    EVENT_CREATED,
    EVENT_MAKER_PROPOSED,
    EVENT_CHECKER_APPROVED,
    EVENT_CHECKER_REJECTED,
    EVENT_AI_TIEBREAK_SUGGESTED,
)

# Exception status projection values (derived cache on models.Exception.status).
STATUS_PENDING_APPROVAL = "pending_approval"
