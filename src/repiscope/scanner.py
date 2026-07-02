"""Discovery of sibling repositories inside the configured root folder.

Everything here is read-only: we look at folder names and README files,
we never create or modify anything.
"""

from pathlib import Path


def find_projects(root: Path, exclude: set[str]) -> list[Path]:
    """Return every direct subfolder of `root` that looks like a project.

    A folder counts as a project when it is not hidden and not excluded.
    """
    projects = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in exclude:
            continue
        projects.append(entry)
    return projects


def one_line_description(project: Path) -> str:
    """Best-effort single-line description of a project, taken from its README.

    Strategy: first non-empty line of the README that isn't a heading or
    an image/badge, truncated to keep list_projects() compact.
    """
    for name in ("README.md", "README.rst", "README.txt", "README"):
        readme = project / name
        if readme.is_file():
            try:
                text = readme.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith(("#", "![", "[!", "<", "---", "===")):
                    continue
                return line[:150]
    return "(no README description)"
