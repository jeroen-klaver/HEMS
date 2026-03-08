"""
CRUD endpoints for solar panel arrays.

GET    /api/v1/solar-arrays         — list all arrays
POST   /api/v1/solar-arrays         — create a new array
PUT    /api/v1/solar-arrays/{id}    — update an existing array
DELETE /api/v1/solar-arrays/{id}    — remove an array
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.database import get_session
from backend.models.readings import SolarArray
from backend.models.schemas import SolarArrayCreateSchema, SolarArraySchema
from backend.services import forecast as forecast_svc

router = APIRouter()


def _to_schema(arr: SolarArray) -> SolarArraySchema:
    return SolarArraySchema(
        id=arr.id,  # type: ignore[arg-type]
        name=arr.name,
        panel_count=arr.panel_count,
        wp_per_panel=arr.wp_per_panel,
        tilt_degrees=arr.tilt_degrees,
        azimuth_degrees=arr.azimuth_degrees,
        enabled=arr.enabled,
        system_kwp=round(arr.panel_count * arr.wp_per_panel / 1000, 3),
    )


@router.get("/solar-arrays", response_model=list[SolarArraySchema])
def list_arrays(session: Session = Depends(get_session)) -> list[SolarArraySchema]:
    """Return all configured solar arrays."""
    arrays = session.exec(select(SolarArray)).all()
    return [_to_schema(a) for a in arrays]


@router.post("/solar-arrays", response_model=SolarArraySchema)
def create_array(
    body: SolarArrayCreateSchema,
    session: Session = Depends(get_session),
) -> SolarArraySchema:
    """Add a new solar array."""
    arr = SolarArray(
        name=body.name,
        panel_count=body.panel_count,
        wp_per_panel=body.wp_per_panel,
        tilt_degrees=body.tilt_degrees,
        azimuth_degrees=body.azimuth_degrees,
        enabled=body.enabled,
    )
    session.add(arr)
    session.commit()
    session.refresh(arr)
    forecast_svc.clear_cache()
    return _to_schema(arr)


@router.put("/solar-arrays/{array_id}", response_model=SolarArraySchema)
def update_array(
    array_id: int,
    body: SolarArrayCreateSchema,
    session: Session = Depends(get_session),
) -> SolarArraySchema:
    """Update an existing solar array."""
    arr = session.get(SolarArray, array_id)
    if not arr:
        raise HTTPException(status_code=404, detail="Solar array not found")
    arr.name = body.name
    arr.panel_count = body.panel_count
    arr.wp_per_panel = body.wp_per_panel
    arr.tilt_degrees = body.tilt_degrees
    arr.azimuth_degrees = body.azimuth_degrees
    arr.enabled = body.enabled
    session.add(arr)
    session.commit()
    session.refresh(arr)
    forecast_svc.clear_cache()
    return _to_schema(arr)


@router.delete("/solar-arrays/{array_id}")
def delete_array(
    array_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Remove a solar array."""
    arr = session.get(SolarArray, array_id)
    if not arr:
        raise HTTPException(status_code=404, detail="Solar array not found")
    session.delete(arr)
    session.commit()
    forecast_svc.clear_cache()
    return {"ok": True}
