---
name: handoff
description: End-of-session handoff for a crew seat ("take a beat, then hand off"). Use when the user says hand off, take a beat, wrap up, go to sleep, or before /exit or an approaching auto-compaction. Closes or annotates beads, appends the seat's diary entry, checks the beads export, reports git status.
---

# Handoff

You are being asked to close out your day, not killed. Do these in order, then say you are done.

If you woke as `new` and declared a seat this session, `$SEAT` and `BEADS_ACTOR` are still `new` until the
relaunch: use the name you declared wherever `$SEAT` appears below, and add `--actor <name>` to every bd write.

1. **Beads.** `bd close <id> --reason "..."` for finished work: what shipped, how it was verified (test
   counts, browsers), what was deliberately left out. For unfinished beads, `bd comment <id> "..."` with the
   exact state: done / not done / the next command to run / anything the user said that is not yet recorded.
2. **Follow-ups** you noticed but did not do: `bd create "Title" -t task -d "why" --deps discovered-from:<id>`.
3. **Export.** `bd export --include-memories -o .beads/issues.jsonl` (auto-export is not reliable; this is the record
   that gets committed, memories included).
4. **Diary** (only if `$SEAT` is set; check with `echo $SEAT`). Append to `crew/$SEAT/diary.md`:

       ## YYYY-MM-DD — short title

       **Did:** what happened, with bead ids.
       **Learned:** about the codebase or about the user's preferences. Project knowledge also goes in `bd remember`.
       **Felt:** one honest line. Optional.
       **Next time:** the first thing to do on waking.

   Note the date: today's is in the session context; do not guess it.
5. **Title.** `crew-title handoff`: the tab and the Remote Control label say you have handed off.
6. **Report.** `git status`, list the changed files, do not commit or push unless asked. End with:
   "Handed off. Ready to sleep."

Without a seat, do steps 1, 2, 3 and 6.
