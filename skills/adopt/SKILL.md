---
name: adopt
description: Set up the crew kit (beads work log, crew seats, handoff) in the current project. Use when the user asks to adopt the crew kit, or to set up beads and crew seats in a project.
---

# Adopt the crew kit

Run from the project root. The kit root is two folders up from this skill's base directory; its README.md
explains seats and beads. Skip any step that is already done. Do not commit unless the user asks.

1. **Beads.** If there is no `.beads/`:
   `bd init --prefix <prefix> --skip-agents --skip-hooks --non-interactive --role maintainer`, then
   `bd config set export.auto true`. The prefix is short, letters only (bd mangles a leading digit into
   `bd_<prefix>-…`), and names the project (acme-shop might use `acme`); ask the user if it is not obvious.
   `bd init` commits on its own ("bd init: initialize beads issue tracking"); unless the user asked for commits,
   undo it with `git reset HEAD~1` while HEAD is still that commit. Check `git check-ignore
   .beads/issues.jsonl` prints nothing: the export must be committable.
2. **A bead for this work**, before any other change: `bd create "Adopt the crew kit" -t task -d "<the user's
   brief, in their words>"`, then `bd update <id> --claim`.
3. **crew/.** Write `crew/README.md`:

       # Crew

       Seats, beads and handoff come from the crew kit: https://github.com/petrklus/crewkit (README.md).
       Wake a seat with `crew-wake <seat>` from the project root; the seats are the folders here, listed in ROSTER.md.

   and `crew/ROSTER.md`:

       # Roster

       Seat names come from the theme in THEME.md.

       | Seat | Pronouns | Declared | Name from | Notes |
       |------|----------|----------|-----------|-------|

   Copy the kit's `THEME.md` (kit root) to `crew/THEME.md`: the Stargate default, which the user may edit
   before seating anyone.
   If the folder name is long, ask the user for a one-word session-name prefix and write it to `crew/prefix`.
4. **Existing task lists.** A TODO.md (or similar) becomes a pointer; its old content stays in git history.
   Name that commit in the pointer:

       # TODO

       Work is tracked in beads (`bd`), not here. This file is only a pointer.

           bd prime                          # the workflow: brief, design, corrections, close reason
           bd ready                          # what can be picked up
           bd list --status in_progress      # what is being worked on
           bd show <id>                      # the why behind a piece of work
           bd list --all                     # everything, closed included
           bd search <text>                  # find a bead; bd memories <word> for project knowledge

       The committed record is `.beads/issues.jsonl`. The old task log is in this file's git history
       (last version: commit <sha>). Session identities and handoff: `crew/README.md`.

   Spec folders (spec-kit `tasks.md` and the like) stay as they are: each spec still in progress gets one
   epic bead that points at its `tasks.md`, not one bead per task. Finished specs get none.
   Other documents that require TODO.md (a spec-kit constitution, say) are the user's to amend: list them for
   them, do not edit them.
5. **CLAUDE.md.** Replace instructions that tell the agent to keep TODO.md with:

       - Update the bead as you go (comments for findings and the user's corrections); do not wait for the end
       - For any work you do, create (or update) its bead; close it with a reason when done. TODO.md is only a pointer to beads, do not write to it.

   and add this section (fill in the prefix):

       ## Beads: the work log (why, not just what)

       Work is tracked in beads (`bd`) with the crew kit (Claude Code plugin `crew@crewkit`, github.com/petrklus/crewkit). `bd prime` is the single source of truth for the workflow; the kit's SessionStart hook runs it at every start, resume, /clear and compaction. If your context did not start with "# Beads workflow", the plugin is missing on this machine: tell the user. In short:

       - A bead exists before code changes. The user's brief and reasons go in the description, decisions in `--design`, their course-corrections in comments, the outcome and verification in the close reason.
       - Beads replaces TODO.md (now a pointer; the old log is in its git history). No TodoWrite or markdown task lists.
       - `.beads/issues.jsonl` is written at handoff and by the SessionEnd hook; commit it with the code. Commits carry a `Bead: <prefix>-xxxx` trailer.
       - Sessions have identities: see `crew/README.md`. End a session with "take a beat, then hand off" (`/crew:handoff`), not `/exit`.

6. **AGENTS.md** (Codex), if the project has one: the same TODO.md replacements, and this section instead
   (Codex has no hooks, so no seats and no automatic prime):

       ## Beads: the work log (why, not just what)

       Work is tracked in beads (`bd`). Run `bd prime` at the start of every session and after compaction: it is the single source of truth for the workflow. In short:

       - A bead exists before code changes. The user's brief and reasons go in the description, decisions in `--design`, their course-corrections in comments, the outcome and verification in the close reason.
       - Beads replaces TODO.md (now a pointer; the old log is in its git history). No markdown task lists.
       - Before you finish, close or comment your beads and run `bd export -o .beads/issues.jsonl`; commit it with the code. Commits carry a `Bead: <prefix>-xxxx` trailer.
       - `crew/` holds the Claude Code seats; leave it alone.

7. **Check and hand over.** `bd export -o .beads/issues.jsonl`. Run the kit's hook as a new session would,
   `echo '{}' | CLAUDE_PROJECT_DIR=$PWD <kit root>/hooks/session-start.sh`, and check it prints the beads
   workflow and "## No seat". Close the bead with what changed and how it was checked. Report `git status`
   and tell the user that `crew/THEME.md` is theirs to edit (where seat names come from), then to seat the
   first crew member with `crew-wake new`.
