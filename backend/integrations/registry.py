"""
Integration plugin registry.

Every integration class decorates itself with @register on import.
The registry maps integration type IDs to their classes, and exposes
helpers used by the API and the scheduler.

Usage in an integration file:
    from hems.integrations.registry import register

    @register
    class EnphaseIQGateway(BaseIntegration):
        manifest = IntegrationManifest(id="enphase_iq_gateway", ...)
        ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.integrations.base import BaseIntegration, IntegrationManifest

# Maps integration type ID → integration class
_registry: dict[str, type[BaseIntegration]] = {}


def register(cls: type[BaseIntegration]) -> type[BaseIntegration]:
    """Class decorator that registers an integration in the global registry.

    The class must have a `manifest` attribute with a unique `id`.
    Raises ValueError if the ID is already registered (catches copy-paste bugs).
    """
    integration_id: str = cls.manifest.id
    if integration_id in _registry:
        raise ValueError(
            f"Integration ID '{integration_id}' is already registered. "
            "Each integration must have a unique manifest.id."
        )
    _registry[integration_id] = cls
    return cls


def get_all_manifests() -> list[IntegrationManifest]:
    """Return manifests for all registered integration types.

    Used by GET /api/v1/integration-types to populate the Settings UI.
    """
    return [cls.manifest for cls in _registry.values()]


def get_class(integration_id: str) -> type[BaseIntegration]:
    """Return the integration class for the given type ID.

    Raises KeyError if the ID is not registered.
    """
    if integration_id not in _registry:
        raise KeyError(
            f"No integration registered with id='{integration_id}'. "
            f"Available: {list(_registry.keys())}"
        )
    return _registry[integration_id]


def is_registered(integration_id: str) -> bool:
    """Check whether a type ID has been registered."""
    return integration_id in _registry
