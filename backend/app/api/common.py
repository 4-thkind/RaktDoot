import json
from datetime import datetime

from fastapi import Header, HTTPException

from ..config import settings


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") + "Z" if dt else None


def sse(data: dict, event: str | None = None) -> str:
    head = f"event: {event}\n" if event else ""
    return f"{head}data: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(401, "Admin token required")
