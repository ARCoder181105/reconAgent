"""routers package constants.

Shared API-surface literals so every router agrees on prefixes, tags, and the
confidence thresholds used to bucket matches into auto/review/verified.
"""
from __future__ import annotations

API_PREFIX = "/api"

# Confidence bucketing (must mirror matcher tier boundaries; kept here so the
# report router can bucket independently of matcher internals).
AUTO_CONF_MIN = 85       # matched: confidence >= 85
REVIEW_CONF_LOW = 60     # review band is [60, 85)
REVIEW_CONF_HIGH = 85

# Tag names for OpenAPI grouping.
TAG_DATA = "data"
TAG_REPORT = "report"
TAG_EXCEPTIONS = "exceptions"
TAG_INSPECTOR = "inspector"
TAG_SCORE = "score"
