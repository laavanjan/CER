"""Registry loader — reads and caches controls_v1.json at startup.

The registry is the source of truth for all 78 controls (5 in this scaffold).
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


def clear_cache() -> None:
    """Clear the in-memory cache (used in tests to reload a custom registry)."""
    global _cache
    with _lock:
        _cache = None
