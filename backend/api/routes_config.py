"""
Integration config CRUD:
  GET    /api/v1/integrations            — list configured instances
  POST   /api/v1/integrations            — add new instance
  PUT    /api/v1/integrations/{id}       — update instance
  DELETE /api/v1/integrations/{id}       — remove instance
  POST   /api/v1/integrations/{id}/test  — test connection
  GET    /api/v1/integration-types       — list available plugin types (for UI)
  PUT    /api/v1/charging/mode           — set charging mode
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend import config as cfg
from backend import scheduler
from backend.database import get_session
from backend.integrations.registry import get_all_manifests, get_class, is_registered
from backend.models.readings import Integration as IntegrationRecord
from backend.models.schemas import (
    ChargingModeUpdateSchema,
    ConfigFieldSchema,
    IntegrationCreateSchema,
    IntegrationInstanceSchema,
    IntegrationTypeSchema,
    IntegrationUpdateSchema,
    TestByConfigSchema,
    TestConnectionSchema,
)

router = APIRouter()

_VALID_MODES = {"off", "min", "solar", "fast"}


# ---------------------------------------------------------------------------
# Integration types (plugin registry → UI)
# ---------------------------------------------------------------------------

@router.get("/integration-types", response_model=list[IntegrationTypeSchema])
async def list_integration_types() -> list[IntegrationTypeSchema]:
    """Return all registered integration plugin types with their config fields."""
    return [
        IntegrationTypeSchema(
            id=m.id,
            name=m.name,
            category=m.category.value,
            description=m.description,
            author=m.author,
            supports_control=m.supports_control,
            icon=m.icon,
            config_fields=[
                ConfigFieldSchema(
                    name=f.name,
                    label=f.label,
                    type=f.type,
                    required=f.required,
                    default=f.default,
                    options=f.options,
                    help_text=f.help_text,
                )
                for f in m.config_fields
            ],
        )
        for m in get_all_manifests()
    ]


@router.post("/integration-types/{type_id}/test", response_model=TestConnectionSchema)
async def test_integration_by_config(
    type_id: str,
    body: TestByConfigSchema,
) -> TestConnectionSchema:
    """Test connectivity using a provided config dict (before saving to DB)."""
    if not is_registered(type_id):
        raise HTTPException(status_code=404, detail=f"Unknown integration type: {type_id}")
    try:
        cls = get_class(type_id)
        instance = cls(body.config)
        success, message = await instance.test_connection()
    except Exception as exc:
        success, message = False, str(exc)
    return TestConnectionSchema(success=success, message=message)


# ---------------------------------------------------------------------------
# Configured instances
# ---------------------------------------------------------------------------

@router.get("/integrations", response_model=list[IntegrationInstanceSchema])
async def list_integrations(session: Session = Depends(get_session)) -> list[IntegrationInstanceSchema]:
    """List all configured integration instances."""
    records = session.exec(select(IntegrationRecord)).all()
    return [
        IntegrationInstanceSchema(
            id=r.id,
            type_id=r.type_id,
            name=r.name,
            enabled=r.enabled,
            last_seen=r.last_seen,
            last_error=r.last_error,
        )
        for r in records
    ]


@router.post("/integrations", response_model=IntegrationInstanceSchema, status_code=201)
async def create_integration(
    body: IntegrationCreateSchema,
    session: Session = Depends(get_session),
) -> IntegrationInstanceSchema:
    """Add a new integration instance."""
    if not is_registered(body.type_id):
        raise HTTPException(status_code=400, detail=f"Unknown integration type: {body.type_id}")
    if session.get(IntegrationRecord, body.id):
        raise HTTPException(status_code=409, detail=f"Integration id '{body.id}' already exists")

    record = IntegrationRecord(
        id=body.id,
        type_id=body.type_id,
        name=body.name,
        config_json=json.dumps(body.config),
        enabled=body.enabled,
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    _reload_scheduler()
    return IntegrationInstanceSchema(id=record.id, type_id=record.type_id,
                                     name=record.name, enabled=record.enabled)


@router.get("/integrations/{integration_id}", response_model=IntegrationInstanceSchema)
async def get_integration(
    integration_id: str,
    session: Session = Depends(get_session),
) -> IntegrationInstanceSchema:
    """Get a single integration including its config (used by the edit form)."""
    record = session.get(IntegrationRecord, integration_id)
    if not record:
        raise HTTPException(status_code=404, detail="Integration not found")
    return IntegrationInstanceSchema(
        id=record.id,
        type_id=record.type_id,
        name=record.name,
        enabled=record.enabled,
        last_seen=record.last_seen,
        last_error=record.last_error,
        config=json.loads(record.config_json),
    )


@router.put("/integrations/{integration_id}", response_model=IntegrationInstanceSchema)
async def update_integration(
    integration_id: str,
    body: IntegrationUpdateSchema,
    session: Session = Depends(get_session),
) -> IntegrationInstanceSchema:
    """Update name, config, or enabled state of an existing integration."""
    record = session.get(IntegrationRecord, integration_id)
    if not record:
        raise HTTPException(status_code=404, detail="Integration not found")

    if body.name is not None:
        record.name = body.name
    if body.config is not None:
        record.config_json = json.dumps(body.config)
    if body.enabled is not None:
        record.enabled = body.enabled

    session.add(record)
    session.commit()
    session.refresh(record)

    _reload_scheduler()
    return IntegrationInstanceSchema(id=record.id, type_id=record.type_id,
                                     name=record.name, enabled=record.enabled,
                                     last_seen=record.last_seen, last_error=record.last_error)


@router.delete("/integrations/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: str,
    session: Session = Depends(get_session),
) -> None:
    """Remove an integration instance."""
    record = session.get(IntegrationRecord, integration_id)
    if not record:
        raise HTTPException(status_code=404, detail="Integration not found")
    session.delete(record)
    session.commit()
    _reload_scheduler()


@router.post("/integrations/{integration_id}/test", response_model=TestConnectionSchema)
async def test_integration(
    integration_id: str,
    session: Session = Depends(get_session),
) -> TestConnectionSchema:
    """Test connectivity for an existing integration instance."""
    record = session.get(IntegrationRecord, integration_id)
    if not record:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        cls = get_class(record.type_id)
        config = json.loads(record.config_json)
        instance = cls(config)
        success, message = await instance.test_connection()
    except Exception as exc:
        success, message = False, str(exc)

    return TestConnectionSchema(success=success, message=message)


# ---------------------------------------------------------------------------
# Charging mode
# ---------------------------------------------------------------------------

@router.put("/charging/mode")
async def set_charging_mode(body: ChargingModeUpdateSchema) -> dict:
    """Set the active charging mode (off | min | solar | fast)."""
    if body.mode not in _VALID_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Choose from: {_VALID_MODES}")

    conf = cfg.get()
    conf.charging.mode = body.mode
    return {"mode": body.mode}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_scheduler() -> None:
    """Rebuild integration instances after a config change."""
    scheduler.reload_instances(cfg.get())
