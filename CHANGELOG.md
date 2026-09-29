# Changelog

Every release of the crew kit and what changed in it, newest first. Versions follow semver (see README,
"Change the kit").

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
