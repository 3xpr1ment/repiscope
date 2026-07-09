# Repiscope

**A periscope for your repos — see everything, touch nothing.**

Repiscope is a read-only MCP server that gives your coding agent (Claude Code,
Cursor, or any MCP client) awareness of the *sibling repositories* next to the
one it's working in — without ever letting it modify them.

## Why

I built a personal assistant to help me decide where my time goes: for that
it needs to know the real state of every project — what changed, what
stalled, what the next step is. So it has to *see* all my repos. But telling
an agent "don't touch anything" is a request, not a guarantee. Repiscope
makes it a **guarantee**: the server exposes zero write tools, so the agent
structurally *cannot* modify your repos. And the same periscope helps any
coding agent working in project A that needs to know how a part of
project B works.

Sandboxes make this worse, not better: mine (rightly) stops the agent from
even *reading* outside the repo it started in without asking. Widening the
sandbox would grant write access too. Repiscope is the third way — the
agent gets structured, read-only sight of every sibling repo through one
MCP server, and the sandbox stays tight.

## See it in action

You're working in `project-a` and need to pull data from another project's
API. Instead of you digging through that codebase, the agent asks Repiscope
directly:

```
You:    Use Repiscope to find out what kind of data I can retrieve
        from billing-api through its API.

Agent:  (calls list_projects → sees "billing-api")
        (calls project_overview "billing-api" → spots src/routes/)
        (calls search "route" project="billing-api")
        (calls read_file "billing-api" "src/routes/invoices.py")

        billing-api exposes three endpoints: /invoices (list, filterable
        by customer and date), /invoices/{id} (full invoice with line
        items), and /customers/{id}/balance (current balance). All
        responses are JSON; auth is a bearer token.
```

The agent explored a repo it has **no ability to write to**. No copy-paste,
no "please don't edit anything," no risk.

## Tools

| Tool | Input | Returns |
|------|-------|---------|
| `list_projects()` | — | every sibling repo + one-line description |
| `project_overview(project)` | repo name | full overview: purpose, stack, structure, recent commits |
| `search(query, project?)` | text, optional repo | files & lines matching the query |
| `read_file(project, path)` | repo + file path | full file contents (size-capped) |
| `store_summary(project, summary)` | repo + your text | caches an agent-written summary (see below) |

## How it stays fresh

Overviews are cached as markdown and refreshed lazily: on each call Repiscope
compares the repo's current git commit hash against the one recorded when the
overview was built. Same hash → serve the cache. Different → rebuild just that
repo's overview. No cron, no daemons.

## Borrowed intelligence

Repiscope has no LLM of its own — no API key, no model calls, zero cost. But
it talks to LLMs all day, so it borrows them: when an overview has no fresh
agent-written summary, it ends with a note asking the *calling* agent to
write one and hand it back via `store_summary`. The summary then opens every
future overview of that project — written by one agent, read by all the
next — until the repo's next commit marks it outdated and the cycle repeats.

## Security by architecture

Repiscope is built so that the safe behaviour is not a promise — it's the
only behaviour possible:

- **Zero repo-write tools.** The server exposes no tool that can create,
  edit or delete anything inside your repositories. The one tool that
  accepts data, `store_summary`, can only write to Repiscope's own cache in
  `~/.cache/repiscope`. An agent cannot misuse a capability that doesn't
  exist.
- **Secrets are invisible.** A single filter (`privacy.py`) is enforced by
  every tool: private keys, certificates (`.pem`, `.pfx`, `.p12`, …),
  `.env*` files, keystores, and anything named like a credential never
  appear in overviews, trees, search results or file reads.
  *Honest limit:* the filter hides sensitive **files** — it does not scrub
  mentions of e.g. a password pasted inside an ordinary text file.
- **Symlinks can't smuggle.** A cloned repo is untrusted content — it may
  contain a symlink like `notes.txt → ~/.ssh/id_rsa`. Anything whose real
  location falls outside the project is invisible to every tool, the secret
  filter also checks a link's real target, and path traversal (`../`) is
  refused.
- **You define the perimeter.** Repiscope only sees the folder you
  explicitly pass (`--root`), and `--exclude` makes chosen repos fully
  invisible — they can't even be resolved by name.
- **It leaves no trace.** Overview caches live in `~/.cache/repiscope`,
  never inside your repositories.

Every claim above is enforced by the test suite in `tests/` — clone the
repo and run `pytest` to check them yourself.

## Quick start

```bash
pip install repiscope
claude mcp add repiscope --scope user -- repiscope --root ~/your/projects/folder
```

That's it — point `--root` at the folder *containing* your repos (not a repo
itself). Optionally hide repos with `--exclude repo-a --exclude repo-b`.
Works with any MCP client; for Claude Desktop there's also a one-click
`.mcpb` bundle (build it with `mcpb/build.sh`).

From source instead:

```bash
git clone https://github.com/3xpr1ment/repiscope.git
cd repiscope
python -m venv .venv && .venv/bin/pip install -e .[dev]
.venv/bin/pytest   # the security claims, as executable proof
```

## Limitations

Honesty section — what Repiscope deliberately does *not* do:

- **The secret filter works at file level.** Sensitive *files* are
  invisible, but a password pasted inside an ordinary `notes.md` will not
  be scrubbed. The perimeter is yours: only point `--root` at folders you
  are comfortable showing to your agent — whatever the tools can see, your
  LLM provider will see too.
- **Search is deliberately dumb.** Case-insensitive substring match, capped
  results, no index, no regex. The calling LLM supplies the intelligence at
  both ends; for heavy code search, use a real code-search tool.
- **Overviews are mechanical.** Without an agent-written summary they are
  README excerpts, language stats and git logs — useful, not insightful.
  The insight arrives once your agents start leaving summaries behind.
- **Read-only cuts both ways.** There is no refresh tool to call: caches
  refresh lazily on the next commit, and stale summaries are served marked
  as stale until an agent writes a new one.
- **Python ≥ 3.11**, developed and tested on macOS; Linux should behave
  identically, Windows symlink semantics are untested.

## Status

v0.2.2 — working and dogfooded daily. Four read-only tools plus borrowed-LLM
summaries, lazy cache refresh, sensitive-file filtering, and a test suite
proving the security claims (path traversal, symlink escapes, secret
filtering — see `tests/`). API may still change.

## How this was built

To be completely clear about authorship: I am not an engineer. Every
architecture decision in Repiscope is mine — what it does, what it refuses
to do, where the security gates live — but the coding itself is done by
Claude (Anthropic's Fable model). My rule for the collaboration: nothing
goes in that I don't understand. The commit history carries the
co-authorship openly, commit by commit.

## License

[MIT](LICENSE)

---

mcp-name: io.github.3xpr1ment/repiscope
