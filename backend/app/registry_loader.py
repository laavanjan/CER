"""Registry loader — reads and caches the controls registry JSON at startup.

The registry is the source of truth for all controls.
It is loaded once and cached in memory for the lifetime of the process.
"""

import json
import threading
from typing import Any

from app.core.config import settings

_cache: list[dict[str, Any]] | None = None
_lock = threading.Lock()


def load(registry_path: str | None = None) -> list[dict[str, Any]]:
    """Load (or return cached) registry controls.

    Parameters
    ----------
    registry_path: Override the default path from settings (useful in tests).

    Returns
    -------
    List of control dicts loaded from controls_v1.json.
    """
    global _cache
    path = registry_path or settings.registry_path

    with _lock:
        if _cache is None:
            with open(path, encoding="utf-8") as fh:
                _cache = json.load(fh)
    return _cache


def get_control(control_id: str, registry_path: str | None = None) -> dict[str, Any] | None:
    """Return a single control dict by its ID, or None if not found."""
    registry = load(registry_path)
    for control in registry:
        if control.get("id") == control_id:
            return control
    return None


def save(controls: list[dict[str, Any]], registry_path: str | None = None) -> None:
    """Persist the controls list to disk and refresh the in-memory cache.

    Parameters
    ----------
    controls: Full list of control dicts to write.
    registry_path: Override the default path from settings (useful in tests).
    """
    global _cache
    path = registry_path or settings.registry_path

    with _lock:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(controls, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        _cache = list(controls)


def upsert_control(
    control_id: str,
    data: dict[str, Any],
    registry_path: str | None = None,
) -> dict[str, Any]:
    """Create or update a control by ID and persist the registry.

    Parameters
    ----------
    control_id: The control's unique identifier (e.g. "GOV-01").
    data: Fields to set on the control (must not include "id").
    registry_path: Override path (tests).

    Returns
    -------
    The updated or newly created control dict.
    """
    registry = list(load(registry_path))
    record = {"id": control_id, **data}

    for idx, control in enumerate(registry):
        if control.get("id") == control_id:
            registry[idx] = record
            save(registry, registry_path)
            return record

    # Not found — append as new
    registry.append(record)
    save(registry, registry_path)
    return record


def delete_control(control_id: str, registry_path: str | None = None) -> bool:
    """Remove a control by ID and persist the registry.

    Parameters
    ----------
    control_id: The control's unique identifier.
    registry_path: Override path (tests).

    Returns
    -------
    True if the control was found and removed, False if it did not exist.
    """
    registry = list(load(registry_path))
    new_registry = [c for c in registry if c.get("id") != control_id]

    if len(new_registry) == len(registry):
        return False

    save(new_registry, registry_path)
    return True


def clear_cache() -> None:
    """Clear the in-memory cache (used in tests to reload a custom registry)."""
    global _cache
    with _lock:
        _cache = None
