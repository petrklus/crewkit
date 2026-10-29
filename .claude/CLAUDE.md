# CLAUDE.md

This repo is the crew kit: the Claude Code plugin `crew@crewkit` (crew seats, the beads work log, handoff)
and its own marketplace. README.md explains the kit; this file is how to work on it.

## Rules for this repo

- The repo is public (MIT). Files, beads and commit messages name no other project and no other project's
  bead ids, and carry no email addresses and no `Claude-Session:` links. Docs use the example project
  `acme-shop` (prefix `acme`). Kit files speak of "the user", not a person by name.
- A kit need found while working in another project becomes a bead here, described without that project's name.
- Releases follow README, "Change the kit": version in `.claude-plugin/plugin.json`, an entry at the top of
  `CHANGELOG.md`, `claude plugin tag .`, `git push --follow-tags`.
- Quality gate (the full check for handoff): `claude plugin validate --strict . && for f in hooks/*.sh bin/crew-*; do sh -n "$f" && echo "ok $f"; done && python3 -I -c 'import ast,sys; [ast.parse(open(f).read(), f) for f in sys.argv[1:]]' hooks/*.py && python3 -I hooks/memories.py selftest`

## Beads: the work log (why, not just what)

Work is tracked in beads (`bd`) with the crew kit (Claude Code plugin `crew@crewkit`, github.com/petrklus/crewkit). `bd prime` is the single source of truth for the workflow; the kit's SessionStart hook runs it at every start, resume, /clear and compaction. If your context has no `# You are <seat>` or `# No seat` line from the crew hook, the plugin is missing on this machine or its output was cut: tell the user. In short:

- A bead exists before code changes. The user's brief and reasons go in the description, decisions in `--design`, their course-corrections in comments, the outcome and verification in the close reason.
- No TODO.md, TodoWrite or markdown task lists.
- `.beads/issues.jsonl` is written at handoff and by the SessionEnd hook; commit it with the code. Commits carry a `Bead: ck-xxxx` trailer.
- Sessions have identities: see `crew/README.md`. End a session with "take a beat, then hand off" (`/crew:handoff`), not `/exit`.
