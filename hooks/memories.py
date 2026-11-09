"""Memories (bd remember) for the crew kit: an index at wake-up, the matching ones with each prompt (ck-6l5).

    memories.py index   prints the topic index for the SessionStart hook; a topic is the key up to its first '-'
    memories.py match   UserPromptSubmit hook: reads the hook JSON on stdin, prints the memories that share words
                        with the prompt as additionalContext, each key once per context (the SessionStart hook
                        clears the seen-file, since it fires whenever a context starts)
    memories.py tool    PreToolUse hook (Bash): reads the hook JSON on stdin, prints the memories whose key topic is
                        a token of the command (curl-..., docker-...) as additionalContext, once per context; a
                        subagent has its own seen-file, so the memory reaches it too (ck-7d3).
                        PostToolUseFailure hook (Bash), same mode: a failed command brings its tool's memories
                        once more, and the memories whose 'Symptom:' line has a phrase found in the error text

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
    print(f"## Memories ({len(m)}): the ones matching a prompt arrive with it, a tool's with its first command; bd memories <word> reads others")
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


def tools(rows, command, seen=()):
    """The memories whose topic (the key up to its first '-') is a token of the command: [(key, value)].

    The author declares the trigger in the key: curl-dev-server-gzip arrives with the first command of a context
    whose tokens include curl (a whole token, the basename of one, or that without its extension: /usr/bin/curl,
    ./runtests.sh). Flags, URLs and paths never equal a topic by accident, so an area topic (qa-, docs-) fires only
    on a command naming it as a word of its own (ls qa). A tool every context runs (bd, git) makes its topic arrive
    in every context. ponytail: tokens only; hostnames, hyphenated tool names (docker-compose) and symptoms in the
    result wait for a memory that needs them.
    """
    toks = set()
    for t in re.split(r"[\s|;&()`]+", command.lower()):
        base = t.rsplit("/", 1)[-1]
        toks.update((t, base, os.path.splitext(base)[0]))
    toks.discard("")
    return capped((k, v) for k, v in rows if k not in seen and k.split("-")[0] in toks)


def symptoms(rows, error, seen=()):
    """The memories with a line 'Symptom: phrase; phrase' of which one phrase occurs in the error text: [(key, value)].

    The author copies the phrases from real error text (Target crashed; Connection refused; Exit code 124). The match
    is a case-insensitive substring; a phrase under four characters counts for nothing. Meant for memories keyed by
    an area, whose trigger is the failure and not a tool: one keyed by a tool comes back when its tool fails anyway.
    """
    low = error.lower()

    def phrases(v):
        return [p.strip(" \t.").lower() for line in re.findall(r"(?im)\bsymptoms?:[ \t]*(.+)$", v) for p in line.split(";")]

    return capped((k, v) for k, v in rows if k not in seen and any(len(p) >= 4 and p in low for p in phrases(v)))


def capped(pairs):
    """At most TOP memories and CAP characters, each key once, in the order given."""
    picked, size = [], 0
    for k, v in pairs:
        if len(picked) < TOP and size + len(k) + len(v) <= CAP and all(k != p for p, _ in picked):
            picked.append((k, v))
            size += len(k) + len(v)
    return picked


def seen_file(hook):
    """The keys already injected into this context: one file per session, and one per subagent inside it."""
    clean = lambda f: re.sub(r"[^A-Za-z0-9_-]", "", str(hook.get(f, "")))
    name = "crew-mem-" + (clean("session_id") or "nosession") + ("-" + clean("agent_id") if clean("agent_id") else "")
    return os.path.join(os.environ.get("TMPDIR") or "/tmp", name)


def inject(hook, picked, head, event, marks=()):
    """Print the picked memories as additionalContext for the hook's event and record their keys (and marks) as seen."""
    if not picked:
        return
    body = "\n\n".join(f"### {k}\n{v}" for k, v in picked)
    out = {"hookEventName": hook.get("hook_event_name") or event, "additionalContext": f"{head}\n\n{body}"}
    print(json.dumps({"hookSpecificOutput": out}))
    try:
        with open(seen_file(hook), "a") as f:
            f.write("".join(k + "\n" for k in [k for k, _ in picked] + list(marks)))
    except OSError:
        pass


def read_hook():
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return None, set()
    try:
        return hook, set(open(seen_file(hook)).read().split())
    except OSError:
        return hook, set()


def match():
    hook, seen = read_hook()
    if hook is None:
        return
    picked = rank(list(memories().items()), str(hook.get("prompt", "")), seen)
    inject(hook, picked, "## Memories matching this prompt (from bd remember; bd memories <key> reads one again)", "UserPromptSubmit")


def tool():
    hook, seen = read_hook()
    if hook is None:
        return
    rows = list(memories().items())
    command = str((hook.get("tool_input") or {}).get("command", ""))
    # The seen-file also holds marks, which never equal a key: @<tool_use_id>:<key> (arrived with that call) and
    # !<key> (arrived at a failure). A failure is the moment a memory matters, so it comes once more per context
    # then, unless it arrived with this very call. A user's interrupt is not a failure.
    call = "@" + re.sub(r"[^A-Za-z0-9_-]", "", str(hook.get("tool_use_id", ""))) + ":"
    if hook.get("hook_event_name") == "PostToolUseFailure":
        if hook.get("is_interrupt"):
            return
        skip = {k for k, _ in rows if "!" + k in seen or call + k in seen}
        picked = capped(symptoms(rows, str(hook.get("error", "")), skip) + tools(rows, command, skip))
        head = "## Memories for this failed command (from bd remember: its tool's, and those whose Symptom line matches the error)"
        inject(hook, picked, head, "PostToolUseFailure", ["!" + k for k, _ in picked])
        return
    picked = tools(rows, command, seen)
    head = "## Memories about a tool this command runs (from bd remember; the key's topic is the tool)"
    inject(hook, picked, head, "PreToolUse", [call + k for k, _ in picked])


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
    rows += [("curl-dev-gzip", "curl against the dev server: --compressed, or Content-Length is stale and curl waits"),
             ("docker-rm-background", "a background docker run --rm trips the harness safety check")]
    gt = lambda c, s=(): [k for k, _ in tools(rows, c, s)]
    assert gt("curl -s --max-time 120 http://localhost:8000/products/3/") == ["curl-dev-gzip"], "the key's topic is a token"
    assert gt("timeout 30 /usr/bin/curl -I localhost:8000 | head -1") == ["curl-dev-gzip"], "a path token, inside a pipeline"
    rows.append(("runtests-keepdb", "./runtests.sh keeps the test database; pass --fresh after a migration"))
    assert gt("./runtests.sh shop.tests") == ["runtests-keepdb"], "a script's basename without its extension"
    assert gt("nohup docker run --rm img >/dev/null 2>&1 &&echo ok") == ["docker-rm-background"], "split on shell operators"
    assert gt("git status && git diff --stat") == [] and gt("cat qa/notes.md") == [], "no token equals a topic: nothing"
    assert len(gt("ls qa")) == TOP, "an area topic named as a bare token fires its memories, capped"
    assert gt("curl -I x", {"curl-dev-gzip"}) == [], "seen keys are skipped on the tool path too"
    rows.append(("headless-webkit", "WebKit dies when the suite runs alongside it.\nSymptom: Target crashed; Connection refused."))
    sy = lambda e, s=(): [k for k, _ in symptoms(rows, e, s)]
    assert sy("Exit code 1\npage.goto: Target crashed at step 3") == ["headless-webkit"], "a declared phrase in the error text"
    assert sy("curl: (7) connection REFUSED") == ["headless-webkit"], "case-insensitive, the closing full stop dropped"
    assert sy("Exit code 1\nAssertionError") == [] and sy("Target crashed", {"headless-webkit"}) == [], "no phrase, or seen: nothing"
    both = capped(symptoms(rows, "Connection refused") + tools(rows, "curl -I x") + tools(rows, "curl -I x"))
    assert [k for k, _ in both] == ["headless-webkit", "curl-dev-gzip"], "a failure: symptom hits first, each key once"
    print("memories.py selftest ok")


if __name__ == "__main__":
    {"index": index, "match": match, "tool": tool, "selftest": selftest}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: None)()
