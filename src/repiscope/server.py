"""Repiscope MCP server.

Exposes exactly four read-only tools. There are — deliberately — no tools
that write, so a connected agent structurally cannot modify sibling repos.

The folder to scan is given explicitly by the user (--root or REPISCOPE_ROOT);
repos listed in --exclude are invisible to every tool.
"""

import argparse
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from repiscope.overview import get_overview
from repiscope.scanner import find_projects, one_line_description

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
def search(query: str, project: str | None = None) -> str:
    """Search inside the code of sibling repos. Returns matching files and lines."""
    return "TODO: not implemented yet"


@mcp.tool()
def read_file(project: str, path: str) -> str:
    """Return the full contents of one file from a sibling repo (read-only, size-capped)."""
    return "TODO: not implemented yet"


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
