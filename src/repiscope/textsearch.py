"""Plain-text search across sibling repos.

Deliberately dumb and predictable: case-insensitive substring match,
line by line. No indexes, no ranking — the calling LLM provides the
intelligence at both ends (choosing the query, interpreting the hits).

Respects the same gates as everything else: noise dirs are skipped and
sensitive files (privacy.py) are never even opened.
"""

from pathlib import Path

from repiscope.overview import NOISE_DIRS
from repiscope.privacy import is_sensitive

MAX_FILE_BYTES = 1_000_000   # don't grep giant artifacts
MAX_HITS_PER_FILE = 5
MAX_HITS_TOTAL = 50
SNIPPET_CHARS = 200


def _searchable_files(project: Path):
    for path in project.rglob("*"):
        rel_parts = path.parts[len(project.parts):]
        if any(part in NOISE_DIRS or part.startswith(".") for part in rel_parts):
            continue
        if not path.is_file() or is_sensitive(path):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def _is_binary(chunk: bytes) -> bool:
    return b"\x00" in chunk


def search_project(project: Path, query: str, budget: int) -> list[str]:
    """Return up to `budget` formatted hits ('file:line: snippet')."""
    needle = query.lower()
    hits = []
    for path in _searchable_files(project):
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if _is_binary(raw[:1024]):
            continue
        text = raw.decode("utf-8", errors="replace")
        per_file = 0
        for lineno, line in enumerate(text.splitlines(), start=1):
            if needle in line.lower():
                rel = path.relative_to(project)
                snippet = line.strip()[:SNIPPET_CHARS]
                hits.append(f"{project.name}/{rel}:{lineno}: {snippet}")
                per_file += 1
                if per_file >= MAX_HITS_PER_FILE or len(hits) >= budget:
                    break
        if len(hits) >= budget:
            break
    return hits
