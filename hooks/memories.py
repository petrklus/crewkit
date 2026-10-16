"""Memories (bd remember) for the crew kit: an index at wake-up, the matching ones with each prompt (ck-6l5).

    memories.py index   prints the topic index for the SessionStart hook; a topic is the key up to its first '-'
    memories.py match   UserPromptSubmit hook: reads the hook JSON on stdin, prints the memories that share words
                        with the prompt as additionalContext, each key once per context (the SessionStart hook
                        clears the seen-file, since it fires whenever a context starts)

Claude Code inlines at most 10,000 characters per hook string; both outputs stay well under it.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys

CAP = 4000  # characters of memory text per prompt
TOP = 5     # memories per prompt
STOP = set("""a an and are as at be but by can do for from has have if in is it its of on or so that the this to was we with you
add build create delete did discussed done fix fixed fixing get got help implement let look make new now okay old read remove run say
said see tell thing things told try update use used using what when where which who why yes
about above after again against almost already also always among around because been before being below
between both change check could does done down each either else even ever every exactly file files find first from give
going good great have having here into just keep know last later less like look made make many maybe might more most
much must need needs never next nothing only other over please really right said same seems shall should show since some
something still such sure take than thank thanks that their them then there these they thing think this those through
time today under until upon very want wants well were what when where whether which while will with within without work
would write your yours""".split())


def memories():
    try:
        out = subprocess.run(["bd", "memories", "--json"], capture_output=True, text=True, timeout=20).stdout
        m = json.loads(out)
    except Exception:
        return {}
    return {k: v for k, v in m.items() if k != "schema_version" and isinstance(v, str)}


def index():
    m = memories()
    if not m:
        return
    topics = {}
    for k in m:
        t = k.split("-")[0]
        topics[t] = topics.get(t, 0) + 1
    print(f"## Memories ({len(m)}): the ones matching a prompt arrive with it; bd memories <word> reads others")
    print(", ".join(f"{t} {n}" for t, n in sorted(topics.items(), key=lambda x: (-x[1], x[0]))))


def match():
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return
    # ponytail: FTS5 (Porter stems, BM25, key weighted 3x) over the prompt's words; embeddings are the upgrade.
    words = {w for w in re.findall(r"[^\W_]+", str(hook.get("prompt", "")).lower()) if len(w) > 1 and w not in STOP}
    if not words:
        return
    sid = re.sub(r"[^A-Za-z0-9_-]", "", str(hook.get("session_id", ""))) or "nosession"
    seen_path = os.path.join(os.environ.get("TMPDIR") or "/tmp", f"crew-mem-{sid}")
    try:
        seen = set(open(seen_path).read().split())
    except OSError:
        seen = set()
    rows = [(k, v) for k, v in memories().items() if k not in seen]
    if not rows:
        return
    db = sqlite3.connect(":memory:")
    db.execute("CREATE VIRTUAL TABLE m USING fts5(key, value, tokenize='porter')")
    db.executemany("INSERT INTO m VALUES (?, ?)", rows)
    query = " OR ".join('"' + w.replace('"', '""') + '"' for w in sorted(words))
    ranked = db.execute("SELECT key, value, bm25(m, 3.0, 1.0) AS s FROM m WHERE m MATCH ? ORDER BY s, key LIMIT ?", (query, TOP)).fetchall()
    picked, size = [], 0
    for k, v, s in ranked:
        if s > 0.4 * ranked[0][2]:  # bm25 is negative, lower is better: drop matches far weaker than the best one
            break
        if size + len(k) + len(v) > CAP:
            break
        picked.append((k, v))
        size += len(k) + len(v)
    if not picked:
        return
    body = "\n\n".join(f"### {k}\n{v}" for k, v in picked)
    ctx = f"## Memories matching this prompt (from bd remember; bd memories <key> reads one again)\n\n{body}"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}))
    try:
        with open(seen_path, "a") as f:
            f.write("".join(k + "\n" for k, _ in picked))
    except OSError:
        pass


if __name__ == "__main__":
    {"index": index, "match": match}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: None)()
