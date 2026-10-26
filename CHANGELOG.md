# Changelog

Every release of the crew kit and what changed in it, newest first. Versions follow semver (see README,
"Change the kit").

## 1.3.1 (2026-10-26)

- Every crew project has `idleCompaction: false` in `.claude/settings.json`: `/crew:adopt` writes it, and the
  SessionStart hook writes it wherever it is missing and says so, since a plugin cannot set it itself (only
  `agent` and `subagentStatusLine` are honoured from a plugin's settings). A compaction replaces a seat's
  memory with a summary; a seat hands off instead.
- The SessionStart hook turns bd's auto-export off where it is still on, so projects adopted before 1.3.0 stop
  warning on every write once their export holds memories.

## 1.3.0 (2026-10-16)

- Claude Code inlines at most 10,000 characters of a hook's output; over that it saves the text to a file and
  shows only the first 2,000. A project with 29 memories pushed the SessionStart output to 24 KB and a seat
  ran a whole session without its identity. Now the seat line is the first line of output, `bd prime` runs
  with `--no-memories`, the memories appear as a topic index, and the whole output is measured and cut at
  9,500 bytes with a note if a seat's files ever push it over.
- Memories scale: a new UserPromptSubmit hook sends the memories that match the prompt along with it (SQLite
  FTS5: stemmed words, BM25 rank; five at most, 4,000 characters, each once per context). `PRIME.md` states
  the key convention `<topic>-<slug>`. Needs bd 1.3 or later.
- `PRIME.md` and the adopt skill's CLAUDE.md section check for the seat line, not for "# Beads workflow":
  the latter was in the 2,000-character preview and passed while the seat was lost.
- Memories are in the committed record: the SessionEnd hook, the handoff skill and the adopt skill export with
  `--include-memories`, so a second machine or a fresh clone has them too (bd leaves them out by default).
  bd's own auto-export cannot write memories and warns on every write once the file holds them, so the adopt
  skill no longer turns `export.auto` on; projects that have it on should run `bd config set export.auto false`.
- Opt-in auto-commit: with a `crew/autocommit` file in the project, the SessionEnd hook (now
  `hooks/session-end.sh`) commits the beads export and the seat's own folder as `chore: <seat>'s handoff`,
  touching nothing else the user has staged and never pushing.
- The kit's own working instructions moved from `CLAUDE.md` to `.claude/CLAUDE.md`: `claude plugin validate
  --strict` took the root file for plugin context and failed the quality gate on the warning.

## 1.2.1 (2026-10-01)

- A seat that wakes as `new` keeps `SEAT=new` and `BEADS_ACTOR=new` until relaunched, so its first handoff
  pointed the diary at `crew/new/` and its first beads were created by `new`. The handoff skill and
  "Adding a seat" now say: use the declared name for `crew/<name>/`, and `--actor <name>` on bd writes.

## 1.2.0 (2026-09-29)

- Configurable theme: seat names come from `crew/THEME.md` (canon, pool, citation shape), which the
  project may edit before seating anyone. `/crew:adopt` writes it from the kit's new `THEME.md`, the
  Stargate default; the kit never overwrites it. Projects without one keep Stargate: the hook's "New seat"
  note names the theme file to use, the project's or the kit's.

## 1.1.1 (2026-09-29)

- `crew-wake` starts a seat that has no `SEAT.md` yet with an initial prompt, so `crew-wake new` sets the
  seat up on its own. Before, the hook's "New seat" note sat in context until the user typed something.

## 1.1.0 (2026-09-29)

First public release.

- Plugin `crew@crewkit`; this repo is its own Claude Code marketplace.
- Hooks: SessionStart primes beads and wakes the seat (card, laurels, last diary entry, beads in progress,
  inbox); SubagentStart tells subagents to log to the lead's bead; SessionEnd exports beads to
  `.beads/issues.jsonl`. All three do nothing in a project without `crew/`.
- `PRIME.md`: the beads rules, copied into each project's `.beads/PRIME.md`.
- Skills: `/crew:handoff` ("take a beat, then hand off") and `/crew:adopt` (set the kit up in a project).
- `bin/crew-wake`: launches a seat with a named session and Remote Control on.
- README: concepts, install, update, adopt, changing the kit. MIT licence.
