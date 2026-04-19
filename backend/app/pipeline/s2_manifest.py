"""S2 — Manifest: clone/unzip repo, build file manifest, mask secrets.

Responsibilities
----------------
1. Clone the GitHub repository (or unzip the uploaded ZIP).
2. Walk the filesystem tree and compute SHA-256 for each file.
3. Detect and mask common secret patterns (API keys, tokens, passwords).
4. Return a list of ManifestEntry objects for downstream stages.

IMPORTANT: files are read as text/bytes only — no code execution takes place.
"""

import hashlib
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from app.pipeline.models import ManifestEntry, ProjectProfile

# Patterns that indicate a secret — matched lines are replaced with redacted text.
_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|credential)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

_MAX_FILE_BYTES = 5 * 1024 * 1024  # skip files > 5 MB


def _sha256(path: Path) -> str:
    """Return hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _mask_secrets(content: str) -> tuple[str, bool]:
    """Replace secret values with '<REDACTED>'. Returns (masked_content, was_masked)."""
    masked = content
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(lambda m: m.group(0).split("=")[0] + "=<REDACTED>", masked)
    return masked, masked != content


def build_manifest(root: Path) -> list[ManifestEntry]:
    """Walk *root* and return a ManifestEntry for every file found."""
    entries: list[ManifestEntry] = []
    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file():
            continue
        size = filepath.stat().st_size
        if size > _MAX_FILE_BYTES:
            continue
        digest = _sha256(filepath)
        masked = False
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
            _, masked = _mask_secrets(text)
        except OSError:
            pass
        entries.append(
            ManifestEntry(
                path=str(filepath.relative_to(root)),
                size_bytes=size,
                sha256=digest,
                masked=masked,
            )
        )
    return entries


def run(profile: ProjectProfile) -> tuple[Path, list[ManifestEntry]]:
    """Clone or unzip the project and return (repo_root, manifest).

    Parameters
    ----------
    profile: Validated project profile from S1.

    Returns
    -------
    A tuple of (repo root directory, list of ManifestEntry).
    """
    if profile.zip_path:
        # Extract supplied ZIP to a temp directory
        tmp = tempfile.mkdtemp(prefix="ethiksa_")
        with zipfile.ZipFile(profile.zip_path, "r") as zf:
            zf.extractall(tmp)
        repo_root = Path(tmp)
    elif profile.github_url:
        tmp = tempfile.mkdtemp(prefix="ethiksa_")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch",
             str(profile.github_url), tmp],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
        repo_root = Path(tmp)
    else:
        raise ValueError("No source provided — should have been caught by S1.")

    manifest = build_manifest(repo_root)
    return repo_root, manifest
