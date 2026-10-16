#!/bin/sh
# SessionEnd hook: write the beads export, memories included. With crew/autocommit present, commit it together
# with the seat's own folder (its diary, a new seat's card): a pathspec commit, so anything else the user has
# staged stays staged and uncommitted. No push (ck-jwt).
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
cat >/dev/null
[ -d crew ] || exit 0
command -v bd >/dev/null 2>&1 || exit 0
bd export --include-memories -o .beads/issues.jsonl -q 2>/dev/null || exit 0
[ -f crew/autocommit ] || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
set -- .beads/issues.jsonl
if [ -n "$SEAT" ] && [ -d "crew/$SEAT" ]; then set -- "$@" "crew/$SEAT"; msg="chore: $SEAT's handoff"; else msg="chore: beads export"; fi
git add -- "$@" 2>/dev/null
git diff --quiet HEAD -- "$@" 2>/dev/null && exit 0
git commit -q -m "$msg" -- "$@" >/dev/null 2>&1 || true
