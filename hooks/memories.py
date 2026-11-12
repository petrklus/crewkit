"""Memories (bd remember) for the crew kit: the pinned ones named at wake-up, the matching ones with each prompt (ck-6l5).

    memories.py index   prints the pinned memories for the SessionStart hook, each as its key and a summary, never its
                        text; a memory is pinned by a line 'Pinned: <summary>' in its text, and the others are not
                        listed at all (ck-3jk.1)
    memories.py match   UserPromptSubmit hook: reads the hook JSON on stdin and prints, as additionalContext, the
                        memories that match the prompt by word and, where recall.py is set up, by meaning: the best
                        one in full, up to five more as key and summary, each once per context (the SessionStart
                        hook clears the seen-file, since it fires whenever a context starts) (ck-3jk.2)
    memories.py tool    PreToolUse hook (Bash): reads the hook JSON on stdin, prints the memories whose key topic
                        names a program the command runs (curl-..., docker-...) as additionalContext, once per context; a
                        subagent has its own seen-file, so the memory reaches it too (ck-7d3). With recall by
                        meaning set to 'commands every', also the ones the command matches by meaning.
                        PostToolUseFailure hook (Bash), same mode: a failed command brings its tool's memories
                        once more, the memories whose 'Symptom:' line has a phrase found in the error text, and
                        the ones the error text matches by meaning

Claude Code inlines at most 10,000 characters per hook string; both outputs stay well under it.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I leaves the script's directory out
import recall  # recall by meaning, with a local model; absent or slow, it answers None and words carry the call

CAP = 4000  # characters of memory text in full per tool call
TOP = 5     # memories by word per prompt, and in full per tool call
SEM = 3     # memories by meaning per lookup
LISTED = 5  # further matches named by key and summary under the one delivered in full
PIN_CAP = 1500  # characters of pinned lines at wake-up, which shares one 10,000-character hook string with the rest
PIN_LINE = 200  # characters of one pinned summary
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


def pinned(rows):
    """The pinned memories, by key: [(key, summary)]. A memory is pinned by a line 'Pinned: <summary>' in its text.

    The summary is the author's one line on what the memory is and when it matters: the wake-up shows that line and
    never the text. A bare 'Pinned:' falls back to the memory's first sentence (see summary).
    """
    return [(k, summary(v)) for k, v in sorted(rows) if re.search(r"(?im)^[ \t]*pinned:", v)]


def summary(text):
    """One line for a memory: what its Pinned line says, else its first sentence. Cut at PIN_LINE characters."""
    m = re.search(r"(?im)^[ \t]*pinned:[ \t]*(\S.*)$", text)
    if m:
        return m.group(1).strip()[:PIN_LINE]
    body = " ".join(l.strip() for l in text.splitlines() if l.strip() and not re.match(r"(?i)[ \t]*(pinned|symptoms?):", l))
    return re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0][:PIN_LINE]


def index():
    m = memories()
    if not m:
        return
    pins = pinned(m.items())
    how = "by word and by meaning" if recall.on() else "by word (crew-recall setup adds matching by meaning)"
    head = f"## Memories ({len(m)}): each arrives with the prompt or command it matches, {how}; bd memories <key> reads one."
    print(head + (" Pinned:" if pins else ""))
    size = 0
    for i, (k, s) in enumerate(pins):
        line = f"- {k}: {s}"
        if size + len(line) > PIN_CAP:
            print(f"- and {len(pins) - i} more pinned, not shown: bd memories pinned")
            break
        print(line)
        size += len(line) + 1


def rank(rows, prompt, seen=()):
    """The memories worth injecting for a prompt, best first: [(key, value)].

    FTS5 with Porter stems, bm25 with the key weighted 3x. A prompt word found in more than a third of the memories
    is dropped (measured per project, only from 10 memories up). A memory qualifies when it matches two kept words,
    or a hyphenated token of the prompt as a phrase (a bead id, crew-wake), or when the prompt had a single term.
    Weak matches are dropped at 40% of the best qualifying score. Lexical: recall.py is the channel by meaning.
    No character cap here: on a real store a 3,400-character memory filled it and the next right ones were dropped,
    so match() delivers one in full and names the rest (ck-3jk.2).
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
    picked, best = [], None
    for k, v, s in db.execute("SELECT key, value, bm25(m, 3.0, 1.0) AS s FROM m WHERE m MATCH ? ORDER BY s, key", (query,)):
        if k not in want:
            continue
        best = s if best is None else best
        if s > 0.4 * best or len(picked) >= TOP:  # bm25 is negative, lower is better
            break
        picked.append((k, v))
    return picked


def merge(lex, sem):
    """One order from the two channels: the keys both found, then the ones by meaning, then the ones by word.

    Measured on a real store (91 memories, 19 prompts): this order put a right memory first for 17 prompts, against
    15 with the words first."""
    both = [k for k in sem if k in lex]
    return both + [k for k in sem if k not in both] + [k for k in lex if k not in both]


def named(prompt, key, text):
    """The prompt names this memory outright: a hyphenated token of it (a bead id, a key, crew-wake) stands in the
    memory. That is what word matching is kept for, and such a match needs no second opinion from the model."""
    flat = lambda t: " " + re.sub(r"[\W_]+", " ", t.lower()).strip() + " "
    hay = flat(key + " " + text)
    return any(flat(t) in hay for t in re.findall(r"[^\W_]+(?:-[^\W_]+)+", prompt.lower()))


def meaning(mem, query, floor, skip=()):
    """The keys the query matches by meaning, best first, over the floor: None when the model is not in use or did
    not answer (then the words decide alone), [] when it answered and nothing came close."""
    got = recall.ask(mem, query)
    return None if got is None else [k for k, s in got if s >= floor and k not in skip][:SEM]


WRAPPERS = {"sudo", "doas", "env", "nohup", "time", "timeout", "xargs", "exec", "command", "builtin", "nice", "setsid", "stdbuf", "watch"}
INTERPRETERS = {"python", "python3", "python2", "sh", "bash", "zsh", "dash", "node", "ruby", "perl"}


def programs(command):
    """The programs a command line runs, by basename without extension: {'curl', 'runtests'}.

    Only the first word of each simple command counts, after any FOO=bar assignments and the wrappers that take a
    command as their argument (sudo, env, timeout 30, xargs); an interpreter also counts its script. Arguments,
    flags, paths, quoted strings and heredoc bodies are never read: a word in test data, a pattern or a path
    fired memories about other tools (ck-88a).
    """
    text = re.sub(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2(?=\n|$)", " ", command, flags=re.S)
    text = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", " ", text).lower()
    text = re.sub(r"\d*[<>]+&?\s*[^\s|;&]*", " ", text)  # redirections: 2>&1, >/dev/null, <file
    name = lambda w: os.path.splitext(w.rsplit("/", 1)[-1])[0]
    out = set()
    for simple in re.split(r"[\n|;&(){}`]+|\$\(", text):
        words = [w for w in simple.split() if not re.match(r"^[a-z_][a-z0-9_]*=", w)]
        wrapped = False
        while words and (name(words[0]) in WRAPPERS or wrapped and (words[0].startswith("-") or re.fullmatch(r"\d+[smhd]?", words[0]))):
            wrapped = True
            words.pop(0)
        if not words:
            continue
        out.add(name(words[0]))
        if name(words[0]) in INTERPRETERS:
            out.add(next((name(w) for w in words[1:] if not w.startswith("-")), ""))  # its script: the first non-flag word
    out.discard("")
    return out


def tools(rows, command, seen=()):
    """The memories whose topic (the key up to its first '-') names a program the command runs: [(key, value)].

    The author declares the trigger in the key: curl-dev-server-gzip arrives with the first command of a context
    that runs curl (curl ..., /usr/bin/curl, sudo timeout 30 curl, and runtests-... with ./runtests.sh or
    python3 runtests.py). A tool every context runs (bd, git) makes its topic arrive in every context. ponytail:
    hostnames and hyphenated tool names (docker-compose) wait for a memory that needs them.
    """
    progs = programs(command)
    return capped((k, v) for k, v in rows if k not in seen and k.split("-")[0] in progs)


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


def deliver(hook, seen, full, listed, mem, head, event, marks=()):
    """Print the memories for a hook: the ones in full [(key, text)], then up to LISTED more keys as key and summary.

    Both are recorded in the seen-file with the marks. A memory arrives in full once per context; one that was only
    named is marked ~key, is not named again, and can still arrive in full when it is the best match later.
    """
    listed = [k for k in dict.fromkeys(listed) if k not in seen and "~" + k not in seen and all(k != f for f, _ in full)][:LISTED]
    if not full and not listed:
        return
    parts = [head] + [f"### {k}\n{v}" for k, v in full]
    if listed:
        lead = "Also matching" if full else "Matching, by key and summary"
        parts.append(f"{lead} (bd memories <key> reads one):\n" + "\n".join(f"- {k}: {summary(mem[k])}" for k in listed))
    out = {"hookEventName": hook.get("hook_event_name") or event, "additionalContext": "\n\n".join(parts)}
    print(json.dumps({"hookSpecificOutput": out}))
    try:
        with open(seen_file(hook), "a") as f:
            f.write("".join(k + "\n" for k in [k for k, _ in full] + ["~" + k for k in listed] + list(marks)))
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
    mem = memories()
    prompt = str(hook.get("prompt", ""))
    lex = [k for k, _ in rank(list(mem.items()), prompt, seen)]
    sem = meaning(mem, prompt, recall.config()["floor"], seen)
    order = merge(lex, sem or [])
    if not order:
        return
    # In full: the best match, when the model found it, or the prompt names it (a bead id, a key), or the model is
    # not in use. A match by word alone that the model did not confirm is named by key and summary, not delivered:
    # on a real store, words alone brought more unrelated memories than right ones.
    first = order[0]
    full = [(first, mem[first])] if sem is None or first in sem or named(prompt, first, mem[first]) else []
    deliver(hook, seen, full, order, mem, "## Memories matching this prompt (from bd remember)", "UserPromptSubmit")


def tool():
    hook, seen = read_hook()
    if hook is None:
        return
    mem = memories()
    rows = list(mem.items())
    command = str((hook.get("tool_input") or {}).get("command", ""))
    cfg = recall.config()
    # The seen-file also holds marks, which never equal a key: @<tool_use_id>:<key> (arrived with that call),
    # !<key> (arrived at a failure) and ~<key> (named by summary). A failure is the moment a memory matters, so it
    # comes once more per context then, unless it arrived with this very call. A user's interrupt is not a failure.
    call = "@" + re.sub(r"[^A-Za-z0-9_-]", "", str(hook.get("tool_use_id", ""))) + ":"
    if hook.get("hook_event_name") == "PostToolUseFailure":
        if hook.get("is_interrupt"):
            return
        error = str(hook.get("error", ""))
        skip = {k for k, _ in rows if "!" + k in seen or call + k in seen}
        picked = capped(symptoms(rows, error, skip) + tools(rows, command, skip))
        # By meaning: what the command printed, without the harness's "Exit code N" line, when it says something;
        # else the command. Not by word: in a live run "command not found" named two memories about other tools.
        said = re.sub(r"(?i)\A\s*exit code \d+\s*", "", error).strip()[:2000]
        sem = None
        if cfg["commands"] != "off":
            sem = meaning(mem, said, cfg["floor"], seen) if len(said) >= 30 else meaning(mem, command, cfg["command_floor"], seen)
        order = sem or []
        head, event, marks = "## Memories for this failed command (from bd remember)", "PostToolUseFailure", ["!" + k for k, _ in picked]
    else:
        picked = tools(rows, command, seen)
        sem = meaning(mem, command, cfg["command_floor"], seen) if cfg["commands"] == "every" else None
        order = sem or []
        head, event, marks = "## Memories for this command (from bd remember)", "PreToolUse", [call + k for k, _ in picked]
    # The author's triggers (the key's tool, a Symptom line) arrive in full. With none, the best match does, when the
    # model found it; the rest are named by key and summary.
    order = [k for k in order if all(k != p for p, _ in picked)]
    if not picked and order and order[0] in (sem or []):
        picked, order = [(order[0], mem[order[0]])], order[1:]
    deliver(hook, seen, picked, order, mem, head, event, marks)


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
    assert gt("git status && git diff --stat") == [] and gt("cat qa/notes.md") == [], "no program is a topic: nothing"
    assert gt("ls qa") == [], "a directory in an argument is not a program (it was, before ck-88a)"
    assert gt("sudo env X=1 timeout 30 curl -I x") == ["curl-dev-gzip"] and gt("python3 runtests.py shop") == ["runtests-keepdb"], "wrappers and interpreters"
    rows += [("release-refresh-copy", "before a release commit, refresh the copy"), ("claude-live-check", "claude -p with --plugin-dir checks the kit live")]
    assert gt("python3 - x <<'PY'\nrelease the thing now\nPY") == [], "a heredoc body is not read"
    assert gt('bd create "Research" -d "a claude.ai doc"') == [] and gt("grep -rn Claude .claude/settings.json") == [], "quoted text, a pattern and a path are not read"
    assert gt("claude -p hi") == ["claude-live-check"] and gt("x=$(curl -s u) && echo $x") == ["curl-dev-gzip"], "the program itself, in a substitution too"
    assert gt("curl -I x", {"curl-dev-gzip"}) == [], "seen keys are skipped on the tool path too"
    rows.append(("headless-webkit", "WebKit dies when the suite runs alongside it.\nSymptom: Target crashed; Connection refused."))
    sy = lambda e, s=(): [k for k, _ in symptoms(rows, e, s)]
    assert sy("Exit code 1\npage.goto: Target crashed at step 3") == ["headless-webkit"], "a declared phrase in the error text"
    assert sy("curl: (7) connection REFUSED") == ["headless-webkit"], "case-insensitive, the closing full stop dropped"
    assert sy("Exit code 1\nAssertionError") == [] and sy("Target crashed", {"headless-webkit"}) == [], "no phrase, or seen: nothing"
    both = capped(symptoms(rows, "Connection refused") + tools(rows, "curl -I x") + tools(rows, "curl -I x"))
    assert [k for k, _ in both] == ["headless-webkit", "curl-dev-gzip"], "a failure: symptom hits first, each key once"
    pn = [("tmp-no-glob", "Never rm /tmp/crew-mem-* by glob.\nPinned: seen-files in /tmp belong to every running seat; before any cleanup there"),
          ("qa-bare", "QA runs against the preview.\nPinned:"), ("tab-prose", "The tab stays pinned: nothing to do.")]
    assert pinned(pn + rows) == [("qa-bare", "QA runs against the preview."), ("tmp-no-glob", pn[0][1].split("Pinned: ")[1])], \
        "a Pinned line pins: its summary, or the first line when bare; 'pinned:' inside a sentence does not"
    assert pinned([("x-long", "Pinned: " + "y" * 500)]) == [("x-long", "y" * PIN_LINE)], "a summary is cut, not the list"
    assert summary("WebKit dies under load. Run it alone.\nSymptom: Target crashed") == "WebKit dies under load.", "the first sentence, not a marker line"
    assert merge(["a", "b", "c"], ["d", "b"]) == ["b", "d", "a", "c"], "found by both, then by meaning, then by word"
    assert merge(["a"], []) == ["a"] and merge([], ["d"]) == ["d"], "either channel alone"
    assert named("any more work on acme-7q1?", "qa-gzip", rows[9][1]) and not named("is the QA page done?", "qa-gzip", rows[9][1]), "a bead id in the prompt names the memory"
    assert named("how does crew-wake pick the id", "wake-id", "crew-wake draws a random id") and not named("re-run it", "x-y", "run it"), "a hyphenated token, whole"
    fill = "Ports, tunnels and logs are described at length here. " * 45
    big = [("mac-host", "The simulator runs safaridriver on the host. " * 4 + fill), ("consent", "The simulator host needs consent before safaridriver attaches."),
           ("paint-lag", "On the simulator safaridriver shows a paint lag on the host. " * 3 + fill)]
    assert len(rank(big, "is safaridriver on the simulator host still fine")) == 3, "two long memories: the second is no longer dropped at 4,000 characters"
    import io, contextlib
    buf, hook = io.StringIO(), {"session_id": "selftest-%d" % os.getpid(), "hook_event_name": "UserPromptSubmit"}
    mem = {"a-one": "First. More.", "b-two": "Second thing.\nPinned: the second, when testing", "c-three": "Third."}
    try:
        with contextlib.redirect_stdout(buf):
            deliver(hook, set(), [("a-one", mem["a-one"])], ["a-one", "b-two", "c-three"], mem, "## H", "UserPromptSubmit")
        ctx = json.loads(buf.getvalue())["hookSpecificOutput"]["additionalContext"]
        assert ctx == "## H\n\n### a-one\nFirst. More.\n\nAlso matching (bd memories <key> reads one):\n- b-two: the second, when testing\n- c-three: Third.", ctx
        assert set(open(seen_file(hook)).read().split()) == {"a-one", "~b-two", "~c-three"}, "in full, and named"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            deliver(hook, {"a-one", "~b-two", "~c-three"}, [], ["b-two", "c-three"], mem, "## H", "UserPromptSubmit")
            deliver(hook, {"a-one", "~b-two"}, [("b-two", mem["b-two"])], ["a-one"], mem, "## H", "UserPromptSubmit")
        assert buf.getvalue().count("hookSpecificOutput") == 1 and "### b-two" in buf.getvalue(), "named once, and still delivered in full later"
    finally:
        os.path.exists(seen_file(hook)) and os.remove(seen_file(hook))
    print("memories.py selftest ok")


if __name__ == "__main__":
    {"index": index, "match": match, "tool": tool, "selftest": selftest}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: None)()
