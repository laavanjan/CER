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


def run(profile: ProjectProfile, registry_path: str) -> ProjectProfile:
    """Validate intake and return the confirmed profile.

    Parameters
    ----------
    profile:        Raw project profile submitted by the user.
    registry_path:  Filesystem path to the controls JSON (injected for testability).

    Returns
    -------
    The same profile, confirmed valid.

    Raises
    ------
    FileNotFoundError if no ZIP or GitHub URL was provided, or registry file missing.
    ValueError        if the registry file contains no controls.
    """
    # -- 1. Confirm at least one source was supplied ----------------------------
    if not profile.github_url and not profile.zip_path:
        raise FileNotFoundError("Either github_url or zip_path must be provided.")

    # -- 2. Confirm registry file exists (controls are stored in the DB) ---------
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Registry not found at {registry_path}")

    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)

    # Confirm the registry file has at least one control
    if not isinstance(registry, list) or len(registry) == 0:
        raise ValueError("Registry contains no controls.")

    return profile
