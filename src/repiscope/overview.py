"""Building and caching per-project overview pages.

The cache lives in the user's cache dir (~/.cache/repiscope), NEVER inside
the scanned repos — Repiscope leaves the sibling folders untouched, always.

Freshness (lazy refresh): every overview records the repo's git commit hash
at build time. On each request we re-read the current hash; same hash →
serve the cache, different (or repo has no git) → rebuild just this one.

Borrowed-LLM summaries: Repiscope has no LLM of its own. When an overview
has no fresh agent-written summary, it ends with a note asking the *calling*
agent to write one and hand it back via the store_summary tool. The summary
is cached next to the overview and served to every future agent until the
repo's next commit.
"""

import subprocess
from collections import Counter
from pathlib import Path

from repiscope.privacy import is_off_limits

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


def git_repos_of(project: Path) -> list[Path]:
    """The git repo(s) backing a project folder.

    Real-world layouts differ: the project folder may be the repo itself,
    or a workspace whose actual repo(s) live one level deeper (e.g.
    Ordifact/app). We check the folder first, then its direct children.
    """
    if (project / ".git").exists():
        return [project]
    repos = []
    for child in sorted(project.iterdir()):
        if child.is_dir() and not child.name.startswith(".") and (child / ".git").exists():
            repos.append(child)
    return repos


def fingerprint(project: Path) -> str:
    """Current identity of the project: combined HEAD hashes of its repo(s).

    '' when no git anywhere — such projects are rebuilt on every call.
    """
    parts = []
    for repo in git_repos_of(project):
        h = _git(repo, "rev-parse", "HEAD")
        if h:
            parts.append(f"{repo.name}:{h}")
    return ";".join(parts)


def cache_path(project: Path) -> Path:
    return CACHE_DIR / f"{project.name}.md"


def summary_path(project: Path) -> Path:
    return CACHE_DIR / f"{project.name}.summary.md"


SUMMARY_MAX_CHARS = 4000

# Appended to an overview whenever it lacks a fresh agent-written summary.
BORROW_NOTE = """## Note to the reading agent

Everything above was assembled mechanically — Repiscope has no LLM of its
own, so it borrows yours. If you now understand this project, leave the next
agent something better: write a short summary (what it is, what it does, how
it is put together; under {max_chars} chars) and call
`store_summary(project="{name}", summary=...)`. It will open every future
overview of this project until its next commit."""


def _read_summary(project: Path) -> tuple[str, str]:
    """(fingerprint-at-write-time, text) of the stored summary; ('', '') if none."""
    f = summary_path(project)
    if not f.is_file():
        return "", ""
    text = f.read_text(encoding="utf-8")
    first, _, rest = text.partition("\n")
    if first.startswith("<!-- fingerprint: ") and first.endswith(" -->"):
        return first[len("<!-- fingerprint: "):-len(" -->")], rest.strip()
    return "", text.strip()


def save_summary(project: Path, summary: str) -> None:
    """Store an agent-written summary, stamped with the repo's current identity.

    Drops the cached overview so the next call rebuilds it with the summary in.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    summary_path(project).write_text(
        f"<!-- fingerprint: {fingerprint(project)} -->\n{summary.strip()}\n",
        encoding="utf-8")
    cache_path(project).unlink(missing_ok=True)


def get_overview(project: Path) -> str:
    """Serve the cached overview if still fresh, else rebuild it (lazy refresh)."""
    current = fingerprint(project)
    cached = cache_path(project)

    if current and cached.is_file():
        text = cached.read_text(encoding="utf-8")
        first_line = text.split("\n", 1)[0]
        if first_line == f"<!-- fingerprint: {current} -->":
            return text

    text = f"<!-- fingerprint: {current} -->\n" + build_overview(project, current)
    if current:  # repos without git are rebuilt every time, nothing to cache against
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_text(text, encoding="utf-8")
    return text


def build_overview(project: Path, current_fingerprint: str) -> str:
    """Assemble the overview page from cheap, mechanical sources."""
    sections = [f"# {project.name}"]

    summary_fp, summary = _read_summary(project)
    summary_fresh = bool(summary) and summary_fp == current_fingerprint
    if summary:
        stale_note = "" if summary_fresh else \
            "\n\n*(written before the latest commits — may be outdated)*"
        sections.append("## Summary (agent-written)\n" + summary + stale_note)

    readme = _readme_excerpt(project)
    if readme:
        sections.append("## README (excerpt)\n" + readme)

    langs = _language_stats(project)
    if langs:
        sections.append("## Languages\n" + langs)

    sections.append("## Structure\n```\n" + _tree(project) + "\n```")

    for repo in git_repos_of(project):
        commits = _git(repo, "log", "-8", "--oneline", "--no-decorate")
        if commits:
            label = "" if repo == project else f" ({repo.name}/)"
            sections.append(f"## Recent commits{label}\n```\n" + commits + "\n```")

    if not summary_fresh:
        sections.append(BORROW_NOTE.format(name=project.name,
                                           max_chars=SUMMARY_MAX_CHARS))

    return "\n\n".join(sections) + "\n"


def _readme_excerpt(project: Path, max_chars: int = 1500) -> str:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        f = project / name
        if f.is_file() and not is_off_limits(f, project):
            try:
                return f.read_text(encoding="utf-8", errors="replace")[:max_chars].strip()
            except OSError:
                pass
    return ""


def _iter_files(project: Path):
    for path in project.rglob("*"):
        if any(part in NOISE_DIRS or part.startswith(".") for part in path.parts[len(project.parts):]):
            continue
        if path.is_file() and not is_off_limits(path, project):
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
        if name.startswith(".") or name in NOISE_DIRS or is_off_limits(entry, project):
            continue
        if entry.is_dir():
            lines.append(f"{name}/")
            for sub in sorted(entry.iterdir())[:6]:
                if sub.name.startswith(".") or sub.name in NOISE_DIRS or is_off_limits(sub, project):
                    continue
                lines.append(f"  {sub.name}{'/' if sub.is_dir() else ''}")
        else:
            lines.append(name)
        if len(lines) >= max_entries:
            lines.append("… (truncated)")
            break
    return "\n".join(lines)
