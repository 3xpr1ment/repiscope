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

## Security by architecture

Repiscope is built so that the safe behaviour is not a promise — it's the
only behaviour possible:

- **Zero write tools.** The server exposes no tool that creates, edits or
  deletes anything. An agent cannot misuse a capability that doesn't exist.
- **Secrets are invisible.** A single filter (`privacy.py`) is enforced by
  every tool: private keys, certificates (`.pem`, `.pfx`, `.p12`, …),
  `.env*` files, keystores, and anything named like a credential never
  appear in overviews, trees, search results or file reads.
- **You define the perimeter.** Repiscope only sees the folder you
  explicitly pass (`--root`), and `--exclude` makes chosen repos fully
  invisible — they can't even be resolved by name.
- **It leaves no trace.** Overview caches live in `~/.cache/repiscope`,
  never inside your repositories.

## Status

🚧 Under construction — v1 in progress.
