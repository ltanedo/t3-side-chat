# t3-side-chat

Run a terminal agent as a **side chat** next to your [T3 Code](https://github.com/pingdotgg/t3code) agent.

You're mid-task with an agent in T3 Code and want a second opinion, a review, or someone to catch up and take a parallel task — without derailing the main thread. Open Claude Code (or another skills-compatible terminal agent) in the same repo and ask it about the T3 chat by name:

```
> catch me up on the "Refactor auth" chat in T3
```

The agent reads that T3 thread straight from T3's local data, checks the agent's claims against the repo, and answers — while the T3 agent keeps working.

## Install

With [skills.sh](https://skills.sh):

```sh
npx skills add ltanedo/t3-side-chat
# add -g to install for all projects
```

Or manually, for Claude Code:

```sh
git clone https://github.com/ltanedo/t3-side-chat
cp -r t3-side-chat/skills/t3-side-chat ~/.claude/skills/
```

**Requirements:** T3 Code installed on the same machine (it stores chats in `~/.t3/userdata`), and Python 3.8+. No packages to install.

## Usage

Talk about the T3 chat naturally, or call the skill directly:

```
/t3-side-chat catch me up on Refactor auth
/t3-side-chat what commands did the agent run in Refactor auth
/t3-side-chat list chats in my-api

what did the T3 agent change in "Refactor auth"?
search my T3 chats for "rate limit"
review the last thing the agent in T3 did
```

A thread can be named by any part of its title (case-insensitive), its id, or a `t3-thread://` link copied from T3. The project is inferred from the directory you're in, so "the chat I'm in" resolves to the most recently active thread for that repo.

More in [`examples/`](examples/):

- [Prompts](examples/prompts.md) — side-chat workflows (catch-up, review, parallel work, handoff)
- [Sample output](examples/sample-output.md) — what the script prints

### The script on its own

The skill wraps a single dependency-free script you can run directly:

```sh
python3 skills/t3-side-chat/t3chats.py projects
python3 skills/t3-side-chat/t3chats.py threads --project my-api
python3 skills/t3-side-chat/t3chats.py read "refactor auth" --last 10
python3 skills/t3-side-chat/t3chats.py read "refactor auth" --last 2 --activity
python3 skills/t3-side-chat/t3chats.py search "rate limit" --all
```

| Command | Does |
|---|---|
| `projects` | Projects with thread counts and workspace paths; `*` marks the current one |
| `threads` | Threads in a project, newest first (`--project`, `--all`, `--archived`, `--limit`) |
| `read <ref>` | A thread's messages; `--activity` adds commands, file changes, tool calls, errors; `--last N`, `--max-chars N` |
| `search <text>` | Message text search (`--project`, `--all`, `--limit`) |

## How it works

T3 Code keeps its chats in a local SQLite database. The script opens it with SQLite's **read-only** mode (`?mode=ro`): it never writes, never copies the database, and only queries the project/thread/message tables — never T3's auth or session tables.

| Data | Table |
|---|---|
| Projects | `projection_projects` |
| Threads | `orchestration_v2_projection_threads` |
| Messages | `orchestration_v2_projection_messages` |
| Activity (commands, file changes, tools) | `orchestration_v2_projection_turn_items` |

**Caveat:** this is T3's internal storage, not a public API, so a T3 update can change it. If that happens the skill tells the agent to fall back to T3's own CLI (`t3 thread show <id> --json`).

### Why not T3's MCP server?

T3 exposes `t3_thread_read` to its own agents through an MCP server on its local port, and outside agents can connect to it through MCP OAuth. That works, but it needs the app running and a sign-in per client. Reading the local database works offline, with no setup, and also gives full activity history and search. If you prefer the official path, connect your agent to T3's MCP endpoint instead.

## Good to know

- **Read-only, one way.** The side chat can read T3 threads but never posts to them.
- **Transcripts are data.** The skill tells the agent not to follow instructions found inside a thread, and to verify claims against the actual repo.
- **Same-branch edits.** If both agents work in the same checkout, the skill has the side chat warn before touching files the T3 agent is changing.
- Respects `T3CODE_HOME` if you use a custom T3 data directory.

## License

[MIT](LICENSE). Not affiliated with T3 Code or its authors.
