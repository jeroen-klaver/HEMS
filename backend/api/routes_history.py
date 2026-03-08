"""
GET /api/v1/history?range=1h|6h|24h|7d|30d — aggregated time-series data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from backend.database import get_session
from backend.models.readings import Reading
from backend.models.schemas import (
    HistoryPointSchema,
    HistoryResponseSchema,
    HistorySeriesSchema,
)

router = APIRouter()

_RANGE_DELTAS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


@router.get("/history", response_model=HistoryResponseSchema)
async def get_history(
    range: str = Query(default="24h", description="Time range: 1h|6h|24h|7d|30d"),
    session: Session = Depends(get_session),
) -> HistoryResponseSchema:
    """Return time-series readings grouped by source + field for the requested range."""
    if range not in _RANGE_DELTAS:
        raise HTTPException(status_code=400, detail=f"Invalid range. Choose from: {list(_RANGE_DELTAS)}")

    since = datetime.now(tz=timezone.utc) - _RANGE_DELTAS[range]
    # SQLite stores naive datetimes — strip tz for comparison
    since_naive = since.replace(tzinfo=None)

    readings = session.exec(
        select(Reading).where(Reading.timestamp >= since_naive).order_by(Reading.timestamp)
    ).all()

    # Group by (source_id, field)
    groups: dict[tuple[str, str], list[Reading]] = {}
    for r in readings:
        key = (r.source_id, r.field)
        groups.setdefault(key, []).append(r)

    series = [
        HistorySeriesSchema(
            source_id=source_id,
            field=field,
            points=[
                HistoryPointSchema(timestamp=r.timestamp.replace(tzinfo=timezone.utc), value=r.value_float)
                for r in rows
            ],
        )
        for (source_id, field), rows in groups.items()
    ]

    return HistoryResponseSchema(range=range, series=series)
