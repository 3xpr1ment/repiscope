"""Repiscope MCP server.

Exposes exactly four read-only tools. There are — deliberately — no tools
that write, so a connected agent structurally cannot modify sibling repos.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("repiscope")


@mcp.tool()
def list_projects() -> str:
    """List every sibling repository with a one-line description."""
    return "TODO: not implemented yet"


@mcp.tool()
def project_overview(project: str) -> str:
    """Return the full overview of one repo: purpose, stack, structure, recent commits."""
    return "TODO: not implemented yet"


@mcp.tool()
def search(query: str, project: str | None = None) -> str:
    """Search inside the code of sibling repos. Returns matching files and lines."""
    return "TODO: not implemented yet"


@mcp.tool()
def read_file(project: str, path: str) -> str:
    """Return the full contents of one file from a sibling repo (read-only, size-capped)."""
    return "TODO: not implemented yet"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
