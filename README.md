# Repiscope

**A periscope for your repos — see everything, touch nothing.**

Repiscope is a read-only MCP server that gives your coding agent (Claude Code,
Cursor, or any MCP client) awareness of the *sibling repositories* next to the
one it's working in — without ever letting it modify them.

## Why

When you run a coding agent inside project A, sometimes it needs to know how
you solved something in project B. Opening project B to the agent is scary:
it might start editing files there. Telling it "don't touch anything" is a
request. Repiscope makes it a **guarantee**: the server exposes zero write
tools, so the agent structurally *cannot* modify your other repos.

## Tools

| Tool | Input | Returns |
|------|-------|---------|
| `list_projects()` | — | every sibling repo + one-line description |
| `project_overview(project)` | repo name | full overview: purpose, stack, structure, recent commits |
| `search(query, project?)` | text, optional repo | files & lines matching the query |
| `read_file(project, path)` | repo + file path | full file contents (size-capped) |

## How it stays fresh

Overviews are cached as markdown and refreshed lazily: on each call Repiscope
compares the repo's current git commit hash against the one recorded when the
overview was built. Same hash → serve the cache. Different → rebuild just that
repo's overview. No cron, no daemons.

## Status

🚧 Under construction — v1 in progress.
