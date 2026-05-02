"""BasePlugin — abstract base class for all S5 analysis plugins.

IMPORTANT CONSTRAINT: Plugins must NEVER execute repository code.
All inspection must be performed by reading files as text or parsed data
(AST, JSON, YAML, TOML, etc.).  Any attempt to import or exec repo code
must be refused.
"""

import abc
from pathlib import Path

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding

_SNIPPET_MAX = 200  # max chars per snippet to avoid bloated output


class BasePlugin(abc.ABC):
    """Abstract base class every plugin must subclass."""

    #: Unique identifier for this plugin — must match entries in controls_v1.json
    plugin_id: str = "base"

    # -- Read-only file helpers ------------------------------------------------

    def read_text(self, repo_root: str, rel_path: str) -> str | None:
        """Safely read a repository file as UTF-8 text.

        Returns None if the file does not exist or cannot be decoded.
        Plugins should use this method instead of open() directly to
        ensure the no-execution constraint is clearly documented.
        """
        full_path = Path(repo_root) / rel_path
        try:
            return full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def filter_manifest(
        self, manifest: list[ManifestEntry], glob_pattern: str
    ) -> list[ManifestEntry]:
        """Return manifest entries whose path matches *glob_pattern*."""
        from fnmatch import fnmatch

        return [e for e in manifest if fnmatch(e.path, glob_pattern)]

    def scan_lines(
        self,
        repo_root: str,
        rel_path: str,
        keywords: list[str],
        reason_prefix: str = "Keyword match",
        case_sensitive: bool = False,
    ) -> list[EvidenceLocation]:
        """Scan a file line-by-line and return one EvidenceLocation per matching line.

        Only the first matching keyword on each line is recorded so a single line
        does not produce multiple locations for the same match.
        """
        content = self.read_text(repo_root, rel_path) or ""
        locations: list[EvidenceLocation] = []
        for line_num, line_text in enumerate(content.splitlines(), start=1):
            compare = line_text if case_sensitive else line_text.lower()
            for kw in keywords:
                needle = kw if case_sensitive else kw.lower()
                if needle in compare:
                    locations.append(
                        EvidenceLocation(
                            file=rel_path,
                            line=line_num,
                            snippet=line_text.strip()[:_SNIPPET_MAX],
                            reason=f"{reason_prefix}: '{kw}'",
                        )
                    )
                    break  # one location per line
        return locations

    def scan_lines_exact(
        self,
        repo_root: str,
        rel_path: str,
        patterns: list[str],
        reason_prefix: str = "Pattern match",
    ) -> list[EvidenceLocation]:
        """Case-sensitive variant of scan_lines used for code patterns."""
        return self.scan_lines(
            repo_root, rel_path, patterns, reason_prefix, case_sensitive=True
        )

    # -- Abstract interface ----------------------------------------------------

    @abc.abstractmethod
    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        """Execute the plugin against the repository.

        Parameters
        ----------
        control_id: The control this invocation targets.
        manifest:   File manifest produced by S2.
        repo_root:  Local path to the materialised repository.

        Returns
        -------
        List of RawFinding objects.  Return an empty list if no relevant
        evidence was found; do NOT raise exceptions for missing evidence.
        """
        ...
