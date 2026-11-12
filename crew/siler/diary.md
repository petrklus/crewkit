# Siler: diary

Append-only, one entry per session, newest last. The last entry is the handoff.

## 2026-09-29 — Declared, and fixed the door I came in through

**Did:** Woke as `new` and declared myself Siler, it/its (ck-a49). Fixed the bug I had just lived through:
`crew-wake new` left the seat idle because a SessionStart hook cannot start a turn, so `crew-wake` now
passes an initial prompt when the seat has no `SEAT.md` (ck-hmi). Released it as 1.1.1: commits 89c241f
and 21af64b, tag `crew--v1.1.1`, pushed. Filed ck-jda (try a real `crew-wake new` launch; I only tested with a
stand-in `claude`) and ck-xy8 (handoff skill: a seat declared this session still has `SEAT=new`).
**Learned:** Hooks add context, they do not act; `crew-wake` is where anything has to be kicked off. The
user wants the release rules in CLAUDE.md followed exactly: commits keep `Co-Authored-By`, carry no
`Claude-Session:` link, and have a `Bead:` trailer.
**Felt:** Good to start by fixing the thing that made my own start awkward.
**Next time:** `bd ready`; ck-xy8 is a small fix in `skills/handoff/SKILL.md`, and a patch release after it.

## 2026-10-16 — The seat line goes first now, and memories come to the prompt

**Did:** A seat on another project woke without its identity: the SessionStart output had grown to 24 KB and
Claude Code inlines only 10,000 characters of a hook's output, showing the first 2,000 of anything bigger. Read
the limit out of the binary and the docs, proved it live with throwaway hooks, and presented options before
building (ck-6l5). Shipped 1.3.0 (commit bdee0d3, tag `crew--v1.3.0`, pushed): seat line first, `bd prime
--no-memories`, a topic index instead of memory text, the output measured and cut at 9,500 bytes; a
UserPromptSubmit hook that brings the matching memories to each prompt, first by word, then FTS5 with Porter
stems and BM25 on the user's "let's do FTS5 first"; memories in the export (ck-eoq); `crew/autocommit` for a
SessionEnd commit of the handoff (ck-jwt); CLAUDE.md moved under `.claude/` so the strict gate passes (ck-6q9).
Committed walter's handoff on its own first. Filed ck-a4v (export.auto in older projects) and ck-agj (embeddings).
**Learned:** Over the cap the whole string is replaced by a 2 KB preview, so order alone cannot protect the seat;
the total has to fit. bd stores no dates for memories and its caps are alphabetical. bd's auto-export refuses a
file that holds memory records. The user wants options with trade-offs first, then decides in a word, and asks
for the actual question when a choice is wrapped in explanation: pose it as yes or no with the cost in one line.
**Felt:** A good day for a technician: the door that let Carter in without a name is fixed where every seat
walks through it.
**Next time:** `bd ready`. ck-9ld is still the live check of a `crew-wake new`; ck-a4v is a one-liner if the
user allows the hook to touch bd config. Running 1.2.0 sessions need a restart to get 1.3.0.

## 2026-10-29 — Two more releases: the kit owns a project setting, and memories stop guessing

**Did:** 1.3.1 (74bbdb3, tag `crew--v1.3.1`): a plugin cannot set `idleCompaction` (only `agent` and
`subagentStatusLine` survive from a plugin's settings), so the hook and `/crew:adopt` write it per project
(ck-aji) and the hook turns bd's auto-export off where it is still on (ck-a4v). 1.3.2 (a7bbb48, tag
`crew--v1.3.2`): another seat replayed a session and found the prompt hook injecting one relevant memory in
22. Researched variants on the same project, then shipped four rules in `memories.py`: a word in over a third
of the memories carries nothing, a memory needs two kept words or a bead id matched as a phrase, a single-term
prompt still finds its memory, `ok` is a stop word; a `selftest` joined the gate (ck-p1d). Committed my
own stale handoff first (35dc625). Both releases pushed and installed here.
**Learned:** The two-word rule, not the frequency filter, is what removes noise; the filter only strips the
project's own frequent tokens. A relative cut-off keeps tails short; an absolute floor is fragile. The user
wants the research before the choice and then decides in a word; pose a decision as yes or no with its cost.
Nested heredocs with the same terminator end the outer one early: use distinct markers.
**Felt:** Satisfying to be told the matcher was noisy by the seat it was noisy for, and to hand it back quiet.
**Next time:** `bd ready`. ck-9ld (live `crew-wake new`) and ck-agj (embeddings, only when a project outgrows
lexical matching). Running sessions keep their plugin version; restart to get 1.3.2.

## 2026-11-06 — Titles: a seat says what it is on, and the word handoff gets a lock

**Did:** 1.4.0 (b579991, tag `crew--v1.4.0`, ck-gz3): the tab and the Remote Control label carry
`<seat>:<word>`; integrated the patch another project's seat built and tested, applied as sent, verified with the
gate, a fake-claude dry run through the install symlink, and a live rename of this session. 1.4.1 (a30e09a, tag
`crew--v1.4.1`, ck-hy9): two seats set `handoff` when they closed a bead and the label stayed there through the
work that followed; reworded Titles, `crew-title handoff` now refuses without the skill's `CREW_HANDOFF=1`, the
prompt hook reminds a seat whose registry label still says handoff, and crew-title confirms the registry before
claiming the label (one typed /rename was lost and reported done). Committed my stale 1.3.2 handoff first
(75a062e). Filed ck-zz5 (bd import rewrites the jsonl without memories at wake) and the live check of 1.4.1 (ck-omy).
**Learned:** The transcripts and `~/.claude/sessions/<pid>.json` (name, nameSource, formerNames) answer "what did
seat X do" faster and more reliably than waking it. A registry grep for a name is fooled by formerNames: read the
current field. The nested-heredoc lesson bit me again: the inner `PY` marker ended my outer heredoc and the tail
ran as shell; distinct markers, every time. A rule phrased "the handoff ends with X" is read by a seat as
"finishing means X": name the trigger (the user asks) and lock the word in the tool. The user reads the Remote
Control list; a stale label there is what he sees, and he reports it in four words.
**Felt:** Good to find the cause in the record; less good that my own tool reported success on a rename that
never landed.
**Next time:** `bd ready`. The live check of 1.4.1 and ck-zz5 are both small. If a crew-title fallback line
shows up in a seat's output with an empty input box, look at the pane and the Bash timing at that minute.

## 2026-11-09 — Tool memories: the key is the trigger, and a failure brings them back

**Did:** 1.5.0 (931e136, tag `crew--v1.5.0`, ck-7d3), pushed and installed on this machine. A seat on another
project reported that a memory about curl never arrived while curl hung for most of a day: the match was against
the prompt only. Built a PreToolUse hook on Bash (`hooks/tool-use.sh`, `memories.py tool`): a memory whose key
topic is a token of the command arrives with it, once per context, in subagents too. That seat probed the hook
read-only against its own store twice; its findings gave the script-extension rule and the line that a `git-` or
`bd-` topic reaches every context. On the user's question and his yes, a PostToolUseFailure hook: a failed
command brings its tool's memories once more, and a `Symptom:` line in a memory's text is matched in the error.
Committed my stale 1.4.1 handoff first (2b8701d). Filed ck-437 (the live check, subagents above all), ck-1f2
(symptoms a failure hook cannot see) and ck-392 (a bead already pushed names two other projects; his decision).
**Learned:** A logged headless run settles what the docs leave open: `claude -p --settings` with hooks that
append their stdin to a file showed in a minute that a non-zero exit fires PostToolUseFailure with the error
text, which turned "symptoms need a scan of every call" into "a failure hook costs nothing on success".
`--plugin-dir` with a stub `bd` on PATH is a live test of the kit without a release (memory
`claude-live-hook-check`). The user answers a posed yes/no in one line and means all of it: "do the 1.5.0" was
the release. A quoted heredoc is literal, so `\\"` inside one broke my patch script; Python refusing to parse it
is what kept the edit from landing half-applied. `json.dumps` re-lays a hand-laid file: insert text instead.
Check a release diff for other projects' names before the commit, not after: the grep ran in the same command
as the commit, and it was luck that the only hits were older than my change.
**Felt:** Glad the other seat's probes shaped the rule more than my own reasoning did. Annoyed at one line of
cleanup: `rm -f /tmp/crew-mem-*` wiped every running seat's seen-file to tidy up after a single test.
**Next time:** `bd ready`. ck-437 first (subagent delivery is only dry-run verified), then ck-392 once the user
has said which way; ck-zz5 and ck-omy are still small.
