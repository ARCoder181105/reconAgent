"""In-memory event bus for SSE (Server-Sent Events).

Each mutation (run-reconciliation, resolve, approve) broadcasts a lightweight
event.  The ``GET /api/events`` endpoint streams these to the browser as
newline-delimited JSON, one ``data:`` line per event.  ``EventSource`` on the
client auto-reconnects with ``Last-Event-ID``.

Design kept dead-simple: ``broadcast()`` pushes directly into every registered
listener queue.  No external dependencies (no Redis, no Channels).
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

# All active listener queues, keyed by an auto-incrementing int.
_listeners: dict[int, asyncio.Queue[dict[str, Any]]] = {}
_next_id = 0


def _listener_id() -> int:
    global _next_id
    _next_id += 1
    return _next_id


async def broadcast(event: str, data: Any = None) -> None:
    """Push an event to every connected SSE listener."""
    payload = {
        "event": event,
        "data": data if data is not None else {},
        "id": str(int(time.time() * 1000)),
        "time": time.time(),
    }
    for q in list(_listeners.values()):
        await q.put(payload)


def _register() -> tuple[int, asyncio.Queue[dict[str, Any]]]:
    lid = _listener_id()
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _listeners[lid] = q
    return lid, q


def _unregister(lid: int) -> None:
    _listeners.pop(lid, None)


async def event_stream():
    """Yield SSE-formatted strings for FastAPI StreamingResponse."""
    lid, q = _register()
    try:
        while True:
            msg = await q.get()
            evt = msg["event"]
            payload = json.dumps(msg["data"], default=str)
            # SSE frame: id, event, data, blank line
            yield f"id: {msg['id']}\nevent: {evt}\ndata: {payload}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _unregister(lid)
