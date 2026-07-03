"""Repiscope MCP server.

Exposes four read-only tools plus store_summary, whose only writable target
is Repiscope's own cache (~/.cache/repiscope). There is — deliberately — no
tool that can touch the repos themselves, so a connected agent structurally
cannot modify them.

The folder to scan is given explicitly by the user (--root or REPISCOPE_ROOT);
repos listed in --exclude are invisible to every tool.
"""

import argparse
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from repiscope.privacy import is_sensitive

from repiscope.overview import SUMMARY_MAX_CHARS, get_overview, save_summary
from repiscope.scanner import find_projects, one_line_description
from repiscope.textsearch import MAX_HITS_TOTAL, search_project

mcp = FastMCP("repiscope")

# Filled in by main() from CLI args / environment before the server starts.
ROOT: Path | None = None
EXCLUDE: set[str] = set()


@mcp.tool()
def list_projects() -> str:
    """List every sibling repository with a one-line description."""
    projects = find_projects(ROOT, EXCLUDE)
    if not projects:
        return f"No projects found in {ROOT}"
    lines = [f"Projects in {ROOT} ({len(projects)}):", ""]
    for p in projects:
        lines.append(f"- {p.name}: {one_line_description(p)}")
    return "\n".join(lines)


def _resolve(project: str) -> Path | None:
    """Map a project name to its folder — only names list_projects() would show.

    This is the security gate: excluded repos and path tricks ('../secrets')
    can never resolve, because we only compare against the scanned list.
    """
    for p in find_projects(ROOT, EXCLUDE):
        if p.name == project:
            return p
    return None


@mcp.tool()
def project_overview(project: str) -> str:
    """Return the full overview of one repo: purpose, stack, structure, recent commits."""
    folder = _resolve(project)
    if folder is None:
        return f"Unknown project '{project}'. Call list_projects() to see valid names."
    return get_overview(folder)


@mcp.tool()
def store_summary(project: str, summary: str) -> str:
    """Store your written summary of a project, shown in every future overview.

    Overviews without a fresh summary end with a note asking you to write one:
    a few paragraphs on what the project is, does, and how it's built. Cached
    until the repo's next commit. This tool can only write to Repiscope's own
    cache — never inside the repos.
    """
    folder = _resolve(project)
    if folder is None:
        return f"Unknown project '{project}'. Call list_projects() to see valid names."
    summary = summary.strip()
    if not summary:
        return "Refused: the summary is empty."
    if len(summary) > SUMMARY_MAX_CHARS:
        return (f"Refused: {len(summary)} chars is over the {SUMMARY_MAX_CHARS} limit — "
                "a summary should be a distillation, not a second overview.")
    save_summary(folder, summary)
    return (f"Stored. project_overview('{project}') now opens with your summary, "
            "until the repo's next commit.")


@mcp.tool()
def search(query: str, project: str | None = None) -> str:
    """Search inside the code of sibling repos. Returns matching files and lines.

    Case-insensitive text match. Give `project` to search one repo,
    omit it to search them all.
    """
    if project is not None:
        folder = _resolve(project)
        if folder is None:
            return f"Unknown project '{project}'. Call list_projects() to see valid names."
        targets = [folder]
    else:
        targets = find_projects(ROOT, EXCLUDE)

    hits: list[str] = []
    for target in targets:
        hits.extend(search_project(target, query, MAX_HITS_TOTAL - len(hits)))
        if len(hits) >= MAX_HITS_TOTAL:
            break

    if not hits:
        where = f"in {project}" if project else f"across {len(targets)} projects"
        return f"No matches for '{query}' {where}."
    capped = " (result limit reached — narrow the query or pass a project)" if len(hits) >= MAX_HITS_TOTAL else ""
    return f"{len(hits)} match(es) for '{query}'{capped}:\n\n" + "\n".join(hits)


MAX_READ_BYTES = 200_000


@mcp.tool()
def read_file(project: str, path: str) -> str:
    """Return the full contents of one file from a sibling repo (read-only, size-capped)."""
    folder = _resolve(project)
    if folder is None:
        return f"Unknown project '{project}'. Call list_projects() to see valid names."

    target = (folder / path).resolve()
    if not target.is_relative_to(folder.resolve()):
        return f"Refused: '{path}' points outside {project}."
    if is_sensitive(target) or any(is_sensitive(Path(p)) for p in target.parts):
        return f"Refused: '{path}' matches the sensitive-file filter."
    if not target.is_file():
        return f"No such file in {project}: '{path}'. Use search() or project_overview() to find files."

    try:
        raw = target.read_bytes()
    except OSError as e:
        return f"Could not read '{path}': {e.strerror}"
    if b"\x00" in raw[:1024]:
        return f"Refused: '{path}' is a binary file."
    truncated = len(raw) > MAX_READ_BYTES
    text = raw[:MAX_READ_BYTES].decode("utf-8", errors="replace")
    note = f"\n\n[… truncated at {MAX_READ_BYTES} bytes — file is {len(raw)} bytes]" if truncated else ""
    return f"── {project}/{path} ──\n{text}{note}"


def main() -> None:
    global ROOT, EXCLUDE
    parser = argparse.ArgumentParser(description="Repiscope — read-only MCP server for sibling repos")
    parser.add_argument("--root", default=os.environ.get("REPISCOPE_ROOT"),
                        help="Folder containing your repos (or set REPISCOPE_ROOT)")
    parser.add_argument("--exclude", nargs="*", default=[],
                        help="Repo names Repiscope must not see at all")
    args = parser.parse_args()

    if not args.root:
        parser.error("no root folder given: pass --root or set REPISCOPE_ROOT")
    ROOT = Path(args.root).expanduser().resolve()
    if not ROOT.is_dir():
        parser.error(f"root folder does not exist: {ROOT}")
    EXCLUDE = set(args.exclude)

    mcp.run()


if __name__ == "__main__":
    main()
