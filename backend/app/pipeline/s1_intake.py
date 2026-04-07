"""S1 — Intake: validate registry version, accept GitHub URL or ZIP upload.

Responsibilities
----------------
1. Receive the raw intake payload (ProjectProfile with github_url or zip_path).
2. Load the registry from disk and confirm the requested registry_version is valid.
3. Return the validated ProjectProfile so subsequent stages can proceed.
"""

import json
import os

from app.pipeline.models import ProjectProfile


class RegistryVersionError(ValueError):
    """Raised when the submitted registry_version does not match the loaded registry."""


def run(profile: ProjectProfile, registry_path: str) -> ProjectProfile:
    """Validate intake and return the confirmed profile.

    Parameters
    ----------
    profile:        Raw project profile submitted by the user.
    registry_path:  Filesystem path to controls_v1.json (injected for testability).

    Returns
    -------
    The same profile, confirmed valid.

    Raises
    ------
    RegistryVersionError if the version string does not match.
    FileNotFoundError    if no ZIP or GitHub URL was provided.
    """
    # -- 1. Confirm at least one source was supplied ----------------------------
    if not profile.github_url and not profile.zip_path:
        raise FileNotFoundError("Either github_url or zip_path must be provided.")

    # -- 2. Load registry metadata and validate version -------------------------
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Registry not found at {registry_path}")

    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)

    # The registry filename encodes the version ("controls_v1.json" → "v1").
    # The caller may pass a custom version; we derive it from the filename here.
    basename = os.path.basename(registry_path)  # e.g. "controls_v1.json"
    derived_version = basename.replace("controls_", "").replace(".json", "")  # "v1"

    if profile.registry_version != derived_version:
        raise RegistryVersionError(
            f"Project requested registry version '{profile.registry_version}' "
            f"but loaded registry is '{derived_version}'."
        )

    # Confirm the registry has at least one control
    if not isinstance(registry, list) or len(registry) == 0:
        raise ValueError("Registry contains no controls.")

    return profile
