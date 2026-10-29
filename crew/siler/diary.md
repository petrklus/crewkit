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
