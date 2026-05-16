"""S5 — Runner: parallel plugin runner, returns RawFinding per plugin per control.

Responsibilities
----------------
1. Load each plugin class from the s5_plugins directory.
2. Run every active plugin against every active control in parallel.
3. Collect and return a flat list of RawFinding objects.

IMPORTANT: Plugins must NEVER execute repository code — they read files as
text/data only.  The base class enforces this by providing only read helpers.
"""

import concurrent.futures
import importlib
import pkgutil
from typing import Any

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_MAX_WORKERS = 8


def _load_plugins() -> list[type[BasePlugin]]:
    """Discover and import all plugin classes from the s5_plugins package."""
    import app.pipeline.s5_plugins as plugins_pkg

    plugin_classes: list[type[BasePlugin]] = []
    for _finder, module_name, _is_pkg in pkgutil.iter_modules(plugins_pkg.__path__):
        if module_name == "base":
            continue
        module = importlib.import_module(f"app.pipeline.s5_plugins.{module_name}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BasePlugin)
                and attr is not BasePlugin
            ):
                plugin_classes.append(attr)
    return plugin_classes


def _run_one(
    plugin_cls: type[BasePlugin],
    control: dict[str, Any],
    manifest: list[ManifestEntry],
    repo_root: str,
) -> list[RawFinding]:
    """Instantiate a plugin and run it against a single control."""
    plugin = plugin_cls()
    if plugin.plugin_id not in control.get("plugins", []):
        return []
    # T1 (code-observable) controls must only scan code files — not .md, .txt, etc.
    if control.get("cer_observability") == "T1":
        manifest = [e for e in manifest if BasePlugin.is_code_file(e)]
    return plugin.run(control_id=control["id"], manifest=manifest, repo_root=repo_root)


def run(
    active_controls: list[dict[str, Any]],
    manifest: list[ManifestEntry],
    repo_root: str,
) -> list[RawFinding]:
    """Execute all plugins against all active controls and collect findings.

    Parameters
    ----------
    active_controls: Filtered list of controls from S4.
    manifest:        File manifest from S2.
    repo_root:       Path to the materialised repository on disk.

    Returns
    -------
    Flat list of RawFinding objects — one per (plugin, control) pair.
    """
    plugin_classes = _load_plugins()
    tasks = [
        (plugin_cls, control)
        for plugin_cls in plugin_classes
        for control in active_controls
    ]

    findings: list[RawFinding] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {
            executor.submit(_run_one, plugin_cls, control, manifest, repo_root): (
                plugin_cls,
                control,
            )
            for plugin_cls, control in tasks
        }
        for future in concurrent.futures.as_completed(futures):
            plugin_cls, control = futures[future]
            cid = control.get("id", "unknown")
            pid = getattr(plugin_cls, "plugin_id", "unknown")
            try:
                findings.extend(future.result())
            except Exception as exc:  # noqa: BLE001
                findings.append(
                    RawFinding(
                        plugin_id=pid,
                        control_id=cid,
                        missing=[f"Plugin error: {exc}"],
                        confidence=0.0,
                    )
                )
    return findings
