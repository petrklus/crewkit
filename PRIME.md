# Beads workflow

Beads (`bd`) is the work log of this repo. Its job is to hold the WHY: in a year, `bd show <id>` (or
`.beads/issues.jsonl` in git history) must explain why the code changed, not just what changed.
Run `bd prime` again after compaction or /clear.

This text comes from the crew kit (github.com/petrklus/crewkit, `PRIME.md`). The SessionStart hook
copies it to `.beads/PRIME.md`; change it in the kit, not here.

## Rules

- A bead exists BEFORE code changes. The user's brief goes in `--description`, in their words, with the reason they
  gave. One bead per deliverable: an epic for a multi-part brief, child tasks with `--parent`. Not one per file.
- Record the why at every step:
  - `--description`: what the user asked and why.
  - `--design`: the approach taken and the alternatives rejected, with the reason for each.
  - `bd comment <id> "..."`: every course-correction from the user ("User: archived counts as not live too,
    because the view redirects archived items") and every finding that changed the plan.
  - `bd close <id> --reason "..."`: what actually shipped, how it was verified (test counts, browsers), what
    was deliberately left out.
- A decision that outlives its task (a convention, "we do not do X because Y") is its own bead:
  `bd create "..." -t decision -d "why" --deps caused-by:<id>`.
- Never falsify the record: failed runs, skipped steps and reverted approaches go in comments and close
  reasons as they happened.
- Do NOT use TodoWrite, TaskCreate or markdown TODO lists. TODO.md is only a pointer, never write to it.
- Project knowledge that is not about one bead (how to run QA, a gotcha) → `bd remember "..."`;
  find it with `bd memories <word>`.
- Subagents work on your behalf: give them the bead id. They record findings with `bd comment <id>` and file
  follow-ups with `bd create --deps discovered-from:<id>`. They never close beads; you do.

## Commands

    bd ready | bd list --status in_progress | bd show <id> | bd search <text> | bd memories <word>
    bd create "Title" -t task|bug|feature|epic|decision -p 0-4 -d "..." --design "..." [--parent <id>] [--deps discovered-from:<id>]
    bd update <id> --claim | bd comment <id> "..." | bd close <id> --reason "..." | bd dep add <issue> <depends-on>

Do not use `bd edit` (opens $EDITOR and blocks).

## Git

- `.beads/issues.jsonl` is the record that goes into git: written by `bd export -o .beads/issues.jsonl` at handoff and
  by the SessionEnd hook. Commit it with the code it explains; never edit it by hand.
- Commits that land a bead carry a trailer line `Bead: <id>`, so `git log --grep 'Bead: <id>'` finds the code.
- The Dolt database in `.beads/embeddeddolt/` is local and untracked; other machines rebuild it from the
  JSONL (`bd import`, run by the SessionStart hook). Do not run `bd dolt push/pull`.
- Do not commit or push unless the user asks.

## Session close: "take a beat, then hand off"

Use the `/crew:handoff` skill: close or annotate beads, run the project's full test suite (the command is in
CLAUDE.md) and record its result, check the export, append your diary entry if you have a seat, report
`git status`.
