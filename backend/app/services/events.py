"""Event recording service."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


async def record_event(
    session: AsyncSession,
    user_id: int,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Event:
    """Record an application event.

    Args:
        session: Active database session.
        user_id: ID of the user who triggered the event.
        event_type: Type/category of the event (e.g., "lesson_started").
        payload: Optional JSON-serializable data associated with the event.

    Returns:
        The created Event instance (not yet committed).
    """
    event = Event(
        user_id=user_id,
        type=event_type,
        payload=payload or {},
    )
    session.add(event)
    return event
