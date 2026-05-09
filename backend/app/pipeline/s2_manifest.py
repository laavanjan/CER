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
import io
import os
import re
import subprocess
import tempfile
import urllib.request
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


def _parse_github_url(github_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL. Returns ('', '') on failure."""
    # Handles: https://github.com/owner/repo and https://github.com/owner/repo.git
    parts = github_url.rstrip("/").rstrip(".git").split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "", ""


def _download_github_zip(github_url: str, token: str, dest_dir: str) -> str:
    """Download repo as a ZIP via GitHub API and extract to dest_dir.

    Returns the commit SHA from the redirect URL, or 'unknown'.
    Works for public repos (no token) and private repos (token required).
    Does NOT invoke git — avoids all credential/TTY issues.
    """
    owner, repo = _parse_github_url(github_url)
    if not owner or not repo:
        raise ValueError(f"Cannot parse GitHub URL: {github_url}")

    # GitHub archive URL — follows redirect to the actual zip
    url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
    api_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"

    commit_sha = "unknown"

    req = urllib.request.Request(api_url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            # The final URL after redirects contains the commit SHA
            final_url = resp.geturl()
            # e.g. https://codeload.github.com/owner/repo/legacy.zip/refs/heads/main?...
            # or   .../archive/{sha}.zip
            zip_data = resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"GitHub download failed ({exc.code}): {exc.reason}. "
            "If the repo is private, set the GITHUB_TOKEN environment variable."
        ) from exc

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        zf.extractall(dest_dir)

    # GitHub zips extract to a single top-level folder like owner-repo-{sha}/
    extracted = [d for d in Path(dest_dir).iterdir() if d.is_dir()]
    if len(extracted) == 1:
        # Try to get commit SHA from folder name: owner-repo-abc1234
        parts = extracted[0].name.rsplit("-", 1)
        if len(parts) == 2 and len(parts[1]) >= 7:
            commit_sha = parts[1]
        # Move contents up one level so repo_root is dest_dir, not the subfolder
        for item in extracted[0].iterdir():
            item.rename(Path(dest_dir) / item.name)
        extracted[0].rmdir()

    return commit_sha


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
        from app.core.config import settings
        tmp = tempfile.mkdtemp(prefix="ethiksa_")
        # Use GitHub API zip download — avoids all git credential/TTY issues (§13)
        commit_sha = _download_github_zip(
            str(profile.github_url), settings.github_token, tmp
        )
        repo_root = Path(tmp)
    else:
        raise ValueError("No source provided — should have been caught by S1.")

    manifest = build_manifest(repo_root)
    workspace_hash = _compute_workspace_hash(manifest)
    return repo_root, manifest, commit_sha, workspace_hash
