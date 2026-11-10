"""Read-only viewer for T3 Code chats (projects, threads, transcripts).

Opens ~/.t3/userdata/statev2.sqlite with SQLite's read-only URI mode, so T3's
data is never written. Only chat/project tables are queried; auth tables are
never touched. The schema is T3's internal storage and may change on update.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = Path(os.environ.get("T3CODE_HOME", Path.home() / ".t3")) / "userdata" / "statev2.sqlite"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def connect():
    if not DB.exists():
        sys.exit(f"T3 database not found at {DB}")
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def norm(path):
    return os.path.normcase(os.path.normpath(path)) if path else ""


def short(text, limit):
    text = "" if text is None else str(text)
    return text if limit <= 0 or len(text) <= limit else text[:limit] + f" …[+{len(text) - limit} chars]"


def projects(con):
    return con.execute(
        """select p.project_id, p.title, p.workspace_root,
                  (select count(*) from orchestration_v2_projection_threads t
                    where t.project_id = p.project_id and t.deleted_at is null) as threads,
                  (select max(t.updated_at) from orchestration_v2_projection_threads t
                    where t.project_id = p.project_id and t.deleted_at is null) as last_active
             from projection_projects p where p.deleted_at is null
            order by last_active desc"""
    ).fetchall()


def resolve_project(con, name):
    """By name/id when given, else the project whose workspace (or a thread's worktree) holds the cwd."""
    rows = projects(con)
    if name:
        for exact in (True, False):
            hits = [r for r in rows if (r["title"].lower() == name.lower() or r["project_id"] == name)
                    or (not exact and name.lower() in r["title"].lower())]
            if len(hits) == 1:
                return hits[0]
            if len(hits) > 1 and not exact:
                sys.exit("Ambiguous project: " + ", ".join(r["title"] for r in hits))
        sys.exit(f"No project matches {name!r}. Run `projects` to list them.")
    cwd = norm(os.getcwd())
    best = None
    for r in rows:
        root = norm(r["workspace_root"])
        if root and (cwd == root or cwd.startswith(root + os.sep)) and (best is None or len(root) > len(norm(best["workspace_root"]))):
            best = r
    if best:
        return best
    for tid, payload in con.execute("select thread_id, payload_json from orchestration_v2_projection_threads where deleted_at is null"):
        wt = norm(json.loads(payload).get("worktreePath"))
        if wt and (cwd == wt or cwd.startswith(wt + os.sep)):
            pid = con.execute("select project_id from orchestration_v2_projection_threads where thread_id=?", (tid,)).fetchone()[0]
            return next(r for r in rows if r["project_id"] == pid)
    return None


def thread_rows(con, project_id=None):
    sql = """select t.thread_id, t.title, t.project_id, t.created_at, t.updated_at, t.archived_at, t.payload_json,
                    p.title as project,
                    (select count(*) from orchestration_v2_projection_messages m where m.thread_id = t.thread_id) as messages
               from orchestration_v2_projection_threads t
               left join projection_projects p on p.project_id = t.project_id
              where t.deleted_at is null"""
    args = ()
    if project_id:
        sql += " and t.project_id = ?"
        args = (project_id,)
    return con.execute(sql + " order by t.updated_at desc", args).fetchall()


def resolve_thread(con, ref, project):
    """Accepts a t3-thread:// or /threads/ link, a thread id or id prefix, or a title substring."""
    ids = UUID_RE.findall(ref)
    pool = thread_rows(con)
    if ids:
        hits = [r for r in pool if r["thread_id"] == ids[-1].lower()]
    else:
        hits = [r for r in pool if r["thread_id"].startswith(ref.lower())] if len(ref) >= 6 else []
        if not hits:
            scoped = [r for r in pool if project is None or r["project_id"] == project["project_id"]]
            hits = [r for r in scoped if r["title"].lower() == ref.lower()] or \
                   [r for r in scoped if ref.lower() in r["title"].lower()]
            if not hits and project is not None:
                hits = [r for r in pool if ref.lower() in r["title"].lower()]
    if not hits:
        sys.exit(f"No thread matches {ref!r}.")
    if len(hits) > 1:
        print(f"{len(hits)} threads match {ref!r}; using the most recently updated. Others:", file=sys.stderr)
        for r in hits[1:8]:
            print(f"  {r['thread_id']}  {r['updated_at'][:16]}  [{r['project']}] {r['title']}", file=sys.stderr)
    return hits[0]


def cmd_projects(con, args):
    here = resolve_project(con, None)
    for r in projects(con):
        mark = "*" if here and r["project_id"] == here["project_id"] else " "
        print(f"{mark} {r['title']:<36} {r['threads']:>4} threads  last {str(r['last_active'])[:16]:<16}  {r['workspace_root'] or ''}")
    if here:
        print("\n* = project for the current directory")


def cmd_threads(con, args):
    project = None if args.all else resolve_project(con, args.project)
    if project is None and not args.all:
        sys.exit("Current directory is not a T3 project. Pass --project NAME or --all.")
    rows = thread_rows(con, project and project["project_id"])
    if not args.archived:
        rows = [r for r in rows if r["archived_at"] is None]
    print(f"# Threads in {project['title'] if project else 'all projects'} (newest first)\n")
    for r in rows[: args.limit]:
        p = json.loads(r["payload_json"])
        extras = [x for x in (p.get("branch") and f"branch {p['branch']}",
                              r["archived_at"] and "archived",
                              p.get("forkedFrom") and "fork") if x]
        proj = "" if project else f"[{r['project']}] "
        print(f"- {r['updated_at'][:16]}  {proj}{r['title']}  ({r['messages']} msgs{', ' + ', '.join(extras) if extras else ''})\n  id {r['thread_id']}")


def render_item(row, max_chars):
    d = json.loads(row["payload_json"])
    t = row["type"]
    ts = (d.get("startedAt") or row["updated_at"] or "")[:19].replace("T", " ")
    if t in ("user_message", "assistant_message"):
        who = "USER" if t == "user_message" else "ASSISTANT"
        return f"\n### {who} · {ts}\n{short(d.get('text'), max_chars)}"
    if t == "command_execution":
        return f"- `$ {short(d.get('input'), 300)}` → exit {d.get('exitCode')}" + \
               (f"\n  ```\n  {short(d.get('output'), min(max_chars, 800))}\n  ```" if d.get("output") else "")
    if t == "file_change":
        return f"- file change: {d.get('fileName')}"
    if t == "dynamic_tool":
        return f"- tool {d.get('toolName')}: {short(d.get('input'), 200)}"
    if t in ("web_search", "file_search"):
        return f"- {t.replace('_', ' ')}: {short(d.get('title') or d.get('pattern') or d.get('patterns'), 200)}"
    if t == "todo_list":
        return f"- todo list: {short(d.get('items') or d.get('todos') or d, 400)}"
    if t == "user_input_request":
        return f"- asked user: {short(d.get('questions'), 300)} → {short(d.get('questionAnswer'), 200)}"
    if t in ("error", "system_notice", "notification", "compaction", "handoff", "subagent", "run_interrupt_result"):
        return f"- [{t}] {short(d.get('title') or d.get('summary') or d.get('message'), 200)}"
    return None  # reasoning, checkpoints, interrupt requests: noise for a side chat


def cmd_read(con, args):
    project = resolve_project(con, args.project) if args.project or not UUID_RE.search(args.thread) else None
    th = resolve_thread(con, args.thread, project)
    p = json.loads(th["payload_json"])
    model = (p.get("modelSelection") or {}).get("model")
    print(f"# {th['title']}\nproject: {th['project']} · id: {th['thread_id']} · branch: {p.get('branch')} · "
          f"model: {model} · created {th['created_at'][:16]} · updated {th['updated_at'][:16]}"
          + (f" · worktree: {p['worktreePath']}" if p.get("worktreePath") else ""))
    if args.activity:
        rows = con.execute(
            """select i.type, i.updated_at, i.payload_json from orchestration_v2_projection_turn_items i
                 join orchestration_v2_turn_item_positions pos
                   on pos.thread_id = i.thread_id and pos.turn_item_id = i.turn_item_id
                where i.thread_id = ? order by pos.ordinal""", (th["thread_id"],)).fetchall()
        lines = [x for x in (render_item(r, args.max_chars) for r in rows) if x]
        # --last counts conversational turns; keep the activity between them
        starts = [i for i, l in enumerate(lines) if l.startswith("\n### USER")]
        cut = starts[-args.last] if args.last and len(starts) > args.last else 0
        if cut:
            print(f"\n(showing activity from the last {args.last} user turns; earlier history omitted)")
        print("\n".join(lines[cut:]))
    else:
        rows = con.execute(
            "select role, created_at, payload_json from orchestration_v2_projection_messages where thread_id=? order by created_at",
            (th["thread_id"],)).fetchall()
        if args.last and len(rows) > args.last:
            print(f"\n(showing last {args.last} of {len(rows)} messages)")
            rows = rows[-args.last:]
        for r in rows:
            d = json.loads(r["payload_json"])
            print(f"\n### {r['role'].upper()} · {r['created_at'][:19].replace('T', ' ')}\n{short(d.get('text'), args.max_chars)}")


def cmd_search(con, args):
    project = None if args.all else resolve_project(con, args.project)
    sql = """select m.thread_id, m.role, m.created_at, m.payload_json, t.title, p.title as project
               from orchestration_v2_projection_messages m
               join orchestration_v2_projection_threads t on t.thread_id = m.thread_id and t.deleted_at is null
               left join projection_projects p on p.project_id = t.project_id
              where json_extract(m.payload_json, '$.text') like ?"""
    params = [f"%{args.text}%"]
    if project:
        sql += " and t.project_id = ?"
        params.append(project["project_id"])
    for r in con.execute(sql + " order by m.created_at desc limit ?", (*params, args.limit)):
        text = json.loads(r["payload_json"]).get("text") or ""
        i = text.lower().find(args.text.lower())
        snippet = text[max(0, i - 80): i + 160].replace("\n", " ")
        print(f"- {r['created_at'][:16]} [{r['project']}] {r['title']} ({r['role']})\n  id {r['thread_id']}\n  …{snippet}…")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("projects", help="List projects with thread counts")
    s = sub.add_parser("threads", help="List threads in a project (default: project for cwd)")
    s.add_argument("--project"); s.add_argument("--all", action="store_true")
    s.add_argument("--archived", action="store_true"); s.add_argument("--limit", type=int, default=25)
    s = sub.add_parser("read", help="Print a thread transcript")
    s.add_argument("thread", help="link, id, id prefix, or title substring")
    s.add_argument("--project"); s.add_argument("--last", type=int, default=0, help="only the last N messages (or user turns with --activity)")
    s.add_argument("--activity", action="store_true", help="include commands, file changes, tool calls")
    s.add_argument("--max-chars", type=int, default=4000, help="truncate each message (0 = no limit)")
    s = sub.add_parser("search", help="Search message text")
    s.add_argument("text"); s.add_argument("--project"); s.add_argument("--all", action="store_true")
    s.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()
    with connect() as con:
        {"projects": cmd_projects, "threads": cmd_threads, "read": cmd_read, "search": cmd_search}[args.cmd](con, args)


if __name__ == "__main__":
    main()
