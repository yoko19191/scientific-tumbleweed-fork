"""Stream bridge — decouples agent workers from SSE endpoints.

A ``StreamBridge`` sits between the background task that runs an agent
(producer) and the HTTP endpoint that pushes Server-Sent Events to
the client (consumer).  This package provides an abstract protocol
(:class:`StreamBridge`) plus a default in-memory implementation backed
by :mod:`asyncio.Queue`.
"""

from .async_provider import make_stream_bridge
from .base import END_SENTINEL, HEARTBEAT_SENTINEL, StreamBridge, StreamEvent
from .memory import MemoryStreamBridge
from .sse import format_sse_frame

__all__ = [
    "END_SENTINEL",
    "HEARTBEAT_SENTINEL",
    "MemoryStreamBridge",
    "StreamBridge",
    "StreamEvent",
    "format_sse_frame",
    "make_stream_bridge",
]
