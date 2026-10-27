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
STOP = set("""a an and are as at be but by can do for from has have if in is it its of ok on or so that the this to was we with you
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


def rank(rows, prompt, seen=()):
    """The memories worth injecting for a prompt, best first: [(key, value)].

    FTS5 with Porter stems, bm25 with the key weighted 3x. A prompt word found in more than a third of the memories
    is dropped (measured per project, only from 10 memories up). A memory qualifies when it matches two kept words,
    or a hyphenated token of the prompt as a phrase (a bead id, crew-wake), or when the prompt had a single term.
    Weak matches are dropped at 40% of the best qualifying score. ponytail: lexical; embeddings are the upgrade.
    """
    text = prompt.lower()
    words = {w for w in re.findall(r"[^\W_]+", text) if len(w) > 1 and w not in STOP}
    phrases = {t.replace("-", " ") for t in re.findall(r"[^\W_]+(?:-[^\W_]+)+", text)}
    if not rows or not (words or phrases):
        return []
    db = sqlite3.connect(":memory:")
    db.execute("CREATE VIRTUAL TABLE m USING fts5(key, value, tokenize='porter')")
    db.executemany("INSERT INTO m VALUES (?, ?)", rows)
    n = len(rows)

    def keys(term):
        return {k for (k,) in db.execute("SELECT key FROM m WHERE m MATCH ?", ('"' + term.replace('"', '""') + '"',))}

    hits, terms = {}, set()
    for w in words:
        ks = keys(w)
        if n >= 10 and len(ks) > n / 3:
            continue
        terms.add(w)
        for k in ks:
            hits.setdefault(k, set()).add(w)
    for p in phrases:
        terms.add(p)
        for k in keys(p):
            hits.setdefault(k, set()).add(p)
    if not terms:
        return []
    want = {k for k, t in hits.items() if len(t) >= 2 or any(" " in x for x in t) or len(terms) < 2} - set(seen)
    if not want:
        return []
    query = " OR ".join('"' + t.replace('"', '""') + '"' for t in sorted(terms))
    picked, size, best = [], 0, None
    for k, v, s in db.execute("SELECT key, value, bm25(m, 3.0, 1.0) AS s FROM m WHERE m MATCH ? ORDER BY s, key", (query,)):
        if k not in want:
            continue
        best = s if best is None else best
        if s > 0.4 * best or size + len(k) + len(v) > CAP or len(picked) >= TOP:  # bm25 is negative, lower is better
            break
        picked.append((k, v))
        size += len(k) + len(v)
    return picked


def match():
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return
    sid = re.sub(r"[^A-Za-z0-9_-]", "", str(hook.get("session_id", ""))) or "nosession"
    seen_path = os.path.join(os.environ.get("TMPDIR") or "/tmp", f"crew-mem-{sid}")
    try:
        seen = set(open(seen_path).read().split())
    except OSError:
        seen = set()
    picked = rank(list(memories().items()), str(hook.get("prompt", "")), seen)
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


def selftest():
    """The smallest set that fails if a rule breaks: python3 -I hooks/memories.py selftest."""
    rows = [(f"qa-note-{i}", f"acme-{i}zz QA note {i} about the project page in 2026") for i in range(9)]
    rows += [("qa-gzip", "QA: curl against the dev server needs gzip, or Content-Length is stale (acme-7q1)"),
             ("hooks-cap", "Claude Code caps hook output at 10,000 characters; the seat line goes first"),
             ("docs-preview", "the docs preview runs on port 3000; QA it with the preview script")]
    got = lambda p: [k for k, _ in rank(rows, p)]
    assert got("any more work on acme-7q1?") == ["qa-gzip"], "a bead id is a phrase hit on its own"
    assert got("is the QA page done?") == [], "words in over a third of the memories carry nothing"
    assert got("why is Content-Length stale from the dev server?") == ["qa-gzip"], "two kept words qualify"
    assert got("gzip?") == ["qa-gzip"], "a single rare term still finds its memory"
    assert got("ok") == [] and got("yes go ahead and commit it") == [], "chit-chat injects nothing"
    assert got("run the docs preview script") == ["docs-preview"], "two words, one memory, no tail"
    assert rank(rows, "hook output is capped", seen={"hooks-cap"}) == [], "seen keys are skipped"
    assert rank(rows[:3], "QA note about the project page") != [], "below 10 memories the df filter is off"
    print("memories.py selftest ok")


if __name__ == "__main__":
    {"index": index, "match": match, "selftest": selftest}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: None)()
