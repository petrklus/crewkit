# Changelog

Every release of the crew kit and what changed in it, newest first. Versions follow semver (see README,
"Change the kit").

## 1.6.0 (2026-11-09)

- The wake-up listed the topics of every memory and said nothing about any of them. Now a memory can be pinned:
  a line `Pinned: <summary>` in its text lists it at every session start as its key and that summary (what it is
  and when it matters; never the text), up to 1,500 characters of pins, ahead of the seat's own files so a long
  diary entry is what the 9,500-byte cut takes. A memory that is not pinned is not listed at all.
- Recall was measured on a real store for the first time (91 memories, 24 labelled cases). Matching by word found
  a right memory for most prompts; what lost memories was the 4,000-character budget, which one long memory
  filled so that the right ones ranked behind it were dropped, and what cost context was the unrelated memories
  that came along in full (27 of them over 19 prompts). So delivery changed: a prompt now brings the best match
  in full and names up to five more by key and summary (the `Pinned:` line, else the first sentence), a count
  decides what is shown and not a character budget, and a memory that was only named can still arrive in full
  later. `PRIME.md` tells the seat to start a memory with that one sentence, to keep it short, and to read a
  named memory when its summary fits the work.
- Recall by meaning, a second channel beside the words, with a model that runs on the machine (nothing is sent
  anywhere): `crew-recall setup` installs ONNX Runtime and EmbeddingGemma 300M into `~/.local/share/crewkit`
  (about 1.5 GB; pip needed; the model is under Google's Gemma terms; the download is a pinned revision checked
  by sha256) and switches it on for every crew project on that machine. A lookup takes about 1.5 seconds and
  0.7 GB while it runs, at most two at once; slow or busy, it answers nothing and the words carry that call. It
  runs with each prompt, with each failed Bash command (on what the command printed) and, by default, with
  every Bash command: `crew-recall set commands failed` keeps it to failures, `off` to prompts, and `crew-recall
  set semantic off` turns the channel off. With the model in use a match by word alone is named, not delivered,
  unless the prompt names the memory outright (a bead id, a key). On the real store, through these hooks: a
  right memory in full for 16 of 19 prompts (14 by word alone), 24 of 26 right memories in full or named (22),
  one unrelated memory in full (3), none in full on 10 unrelated prompts (3), and a right memory for 4 of 5
  commands and errors (2). The model was chosen among six, from 23M to 0.6B parameters; the larger ones were
  slower and no better there. One store, a small sample.
- `crew-recall status` shows what is installed and switched on, `crew-recall test "<text>"` what a prompt (or
  with `--command`, a command) would match and with what score. The wake-up line says which way memories are
  matched on the machine.
- The tool trigger read every token of a command, so a word in a heredoc of test data, a grep pattern and a
  path fired memories about other tools. Now it reads only the programs the command runs: the first word of
  each simple command, past `FOO=bar` and wrappers such as `sudo`, `env` and `timeout 30`, plus an interpreter's
  script, so `python3 runtests.py` still brings a `runtests-` memory. `ls qa` no longer brings the `qa-`
  memories: a directory in an argument is not a program. The key's tool and the `Symptom:` line still bring a
  memory in full, and still work with no model.

## 1.5.0 (2026-11-06)

- A memory about how a tool behaves here (curl needs `--compressed` against the dev server; a background
  `docker run --rm` trips the harness check) never arrived: the match was against the prompt, and the moment
  such a memory matters is a command. Now the author declares the trigger in the key's topic (`curl-`,
  `docker-`, `playwright-`), and a PreToolUse hook on Bash sends the memories whose topic is a token of the
  command (a whole token or the basename of a path, never a flag, URL or path) along with its result, up to five
  and each once per context; a subagent gets its own once. Same store, same `bd remember`; the rule is in
  PRIME.md. Existing tool memories keyed by an area (`dev-server-curl-...`) need re-keying by the tool. A script
  counts by its name without the extension (`./runtests.sh` fires `runtests-`), and a tool every context runs
  (`git-`, `bd-`) reaches every context.
- A failed Bash command (a non-zero exit or the harness timeout) is the moment such a memory matters: a
  PostToolUseFailure hook sends the failed command's tool memories once more per context, unless they arrived
  with that very call, and the memories that declare the failure in their text with a line
  `Symptom: <phrase>; <phrase>` (phrases copied from real error text, matched in the error whatever the case),
  for memories keyed by an area. A command that exits zero is not a failure; a user's interrupt is not one
  either.

## 1.4.1 (2026-11-03)

- Seats set `handoff` when they closed a bead: "the handoff ends with crew-title handoff" read as "finished
  means handoff", and the label then stayed `handoff` through the work that followed. PRIME.md's "Titles" now
  says a closed bead changes nothing; `crew-title handoff` refuses unless the handoff skill runs it
  (`CREW_HANDOFF=1`); the prompt hook reminds a seat whose label still says `handoff` to set its word.
  `crew-title` also waits for the session registry to show the new label and says so when the typed `/rename`
  did not land (seen once), instead of reporting success.

## 1.4.0 (2026-10-29)

- The tab (tmux window) and the Remote Control label say what a seat is on. `crew-wake` names the window
  `<seat>:new` and the session `<prefix>_<seat>_<id>:new`; the new `bin/crew-title <word>` (on the session's
  PATH, no install step) renames both when the seat starts on a bead, and the handoff ends with
  `crew-title handoff`. The label changes through `/rename` typed into the session's own input, the only road a
  session has to it; a draft in the input is left alone and the `/rename` line printed instead. The rule is in
  PRIME.md ("Titles").

## 1.3.2 (2026-10-27)

- The memories that arrive with a prompt are the ones that match it, not the ones that share one common word.
  A prompt word found in over a third of the project's memories (its bead prefix, the year) is dropped; a
  memory qualifies on two kept words, or on a bead id or other hyphenated token matched as a phrase, or when
  the prompt has a single term. On a project with 55 memories, six chit-chat and bead-status prompts went from
  five injected memories each to none, and every real hit stayed. `memories.py selftest` guards the rules and
  is part of the quality gate.

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
