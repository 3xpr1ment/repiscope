"""Building and caching per-project overview pages.

The cache lives in the user's cache dir (~/.cache/repiscope), NEVER inside
the scanned repos — Repiscope leaves the sibling folders untouched, always.

Freshness (lazy refresh): every overview records the repo's git commit hash
at build time. On each request we re-read the current hash; same hash →
serve the cache, different (or repo has no git) → rebuild just this one.
"""

import subprocess
from collections import Counter
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "repiscope"

# Folders that would pollute the structure view / language stats.
NOISE_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__",
              "dist", "build", ".next", ".cache", "target"}

LANGUAGES = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
             ".tsx": "TypeScript/React", ".jsx": "JavaScript/React",
             ".html": "HTML", ".css": "CSS", ".go": "Go", ".rs": "Rust",
             ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".sql": "SQL",
             ".sh": "Shell", ".md": "Markdown"}


def _git(project: Path, *args: str) -> str:
    """Run a read-only git command inside the project; '' if it fails."""
    try:
        out = subprocess.run(["git", "-C", str(project), *args],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def fingerprint(project: Path) -> str:
    """Current identity of the repo: its HEAD commit hash ('' if no git)."""
    return _git(project, "rev-parse", "HEAD")


def cache_path(project: Path) -> Path:
    return CACHE_DIR / f"{project.name}.md"


def get_overview(project: Path) -> str:
    """Serve the cached overview if still fresh, else rebuild it (lazy refresh)."""
    current = fingerprint(project)
    cached = cache_path(project)

    if current and cached.is_file():
        text = cached.read_text(encoding="utf-8")
        first_line = text.split("\n", 1)[0]
        if first_line == f"<!-- fingerprint: {current} -->":
            return text

    text = f"<!-- fingerprint: {current} -->\n" + build_overview(project)
    if current:  # repos without git are rebuilt every time, nothing to cache against
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_text(text, encoding="utf-8")
    return text


def build_overview(project: Path) -> str:
    """Assemble the overview page from cheap, mechanical sources."""
    sections = [f"# {project.name}"]

    readme = _readme_excerpt(project)
    if readme:
        sections.append("## README (excerpt)\n" + readme)

    langs = _language_stats(project)
    if langs:
        sections.append("## Languages\n" + langs)

    sections.append("## Structure\n```\n" + _tree(project) + "\n```")

    commits = _git(project, "log", "-8", "--oneline", "--no-decorate")
    if commits:
        sections.append("## Recent commits\n```\n" + commits + "\n```")

    return "\n\n".join(sections) + "\n"


def _readme_excerpt(project: Path, max_chars: int = 1500) -> str:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        f = project / name
        if f.is_file():
            try:
                return f.read_text(encoding="utf-8", errors="replace")[:max_chars].strip()
            except OSError:
                pass
    return ""


def _iter_files(project: Path):
    for path in project.rglob("*"):
        if any(part in NOISE_DIRS or part.startswith(".") for part in path.parts[len(project.parts):]):
            continue
        if path.is_file():
            yield path


def _language_stats(project: Path, top: int = 4) -> str:
    counts = Counter(LANGUAGES[p.suffix] for p in _iter_files(project) if p.suffix in LANGUAGES)
    if not counts:
        return ""
    total = sum(counts.values())
    return ", ".join(f"{lang} ({100 * n // total}%)" for lang, n in counts.most_common(top))


def _tree(project: Path, max_entries: int = 40) -> str:
    """Two-level folder sketch, capped so huge repos stay readable."""
    lines = []
    for entry in sorted(project.iterdir()):
        name = entry.name
        if name.startswith(".") or name in NOISE_DIRS:
            continue
        if entry.is_dir():
            lines.append(f"{name}/")
            for sub in sorted(entry.iterdir())[:6]:
                if sub.name.startswith(".") or sub.name in NOISE_DIRS:
                    continue
                lines.append(f"  {sub.name}{'/' if sub.is_dir() else ''}")
        else:
            lines.append(name)
        if len(lines) >= max_entries:
            lines.append("… (truncated)")
            break
    return "\n".join(lines)
