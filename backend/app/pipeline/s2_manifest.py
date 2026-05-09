"""S2 — Repository Ingestion: clone/unzip, build manifest, mask secrets.

Responsibilities
----------------
1. Clone the GitHub repository (or unzip the uploaded ZIP).
2. Capture commit_sha from git HEAD for audit reproducibility.
3. Walk the filesystem tree and compute SHA-256 per file.
4. Detect and mask common secret patterns before any content is stored.
5. Compute workspace_hash (SHA-256 of the full sorted manifest) for audit seal.
6. Return (repo_root, manifest, commit_sha, workspace_hash).

IMPORTANT: files are read as text/bytes only — no code execution takes place (§13).
"""

import hashlib
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from app.pipeline.models import ManifestEntry, ProjectProfile

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|credential)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

_MAX_FILE_BYTES = 5 * 1024 * 1024  # skip files > 5 MB


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _mask_secrets(content: str) -> tuple[str, bool]:
    masked = content
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(lambda m: m.group(0).split("=")[0] + "=<REDACTED>", masked)
    return masked, masked != content


def _compute_workspace_hash(entries: list[ManifestEntry]) -> str:
    """SHA-256 over sorted 'path:sha256' pairs — stable across runs for same content."""
    h = hashlib.sha256()
    for entry in sorted(entries, key=lambda e: e.path):
        h.update(f"{entry.path}:{entry.sha256}\n".encode())
    return h.hexdigest()


def _get_commit_sha(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
    )
    if result.returncode == 0:
        return result.stdout.decode().strip()
    return "unknown"


def build_manifest(root: Path) -> list[ManifestEntry]:
    entries: list[ManifestEntry] = []
    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file():
            continue
        size = filepath.stat().st_size
        if size > _MAX_FILE_BYTES:
            continue
        digest = _sha256_file(filepath)
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


def run(profile: ProjectProfile) -> tuple[Path, list[ManifestEntry], str, str]:
    """Clone or unzip the project and return (repo_root, manifest, commit_sha, workspace_hash).

    Parameters
    ----------
    profile: Validated project profile from S1.

    Returns
    -------
    (repo_root, manifest, commit_sha, workspace_hash)
    """
    if profile.zip_path:
        tmp = tempfile.mkdtemp(prefix="ethiksa_")
        with zipfile.ZipFile(profile.zip_path, "r") as zf:
            zf.extractall(tmp)
        repo_root = Path(tmp)
        commit_sha = "zip-upload"
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
        commit_sha = _get_commit_sha(repo_root)
    else:
        raise ValueError("No source provided — should have been caught by S1.")

    manifest = build_manifest(repo_root)
    workspace_hash = _compute_workspace_hash(manifest)
    return repo_root, manifest, commit_sha, workspace_hash
