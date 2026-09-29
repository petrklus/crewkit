#!/bin/sh
# SessionStart hook: prime beads (the work log), then wake the seat (README.md of the kit).
# Plain stdout is added to the session context. Fires on startup, resume, clear and compact.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
in=$(cat)
# Only projects that adopted the kit (/crew:adopt) have crew/; everywhere else the plugin stays silent.
[ -d crew ] || exit 0
kit=$(cd "$(dirname "$0")/.." && pwd)
# Inside a subagent the SubagentStart hook already spoke; do not hand a subagent a seat.
printf '%s' "$in" | grep -q '"agent_id" *: *"[^"]' && exit 0
if ! command -v bd >/dev/null 2>&1; then
  echo "beads: bd is not installed on this machine (npm install -g @beads/bd). Work tracking is OFF; tell the user before doing anything else."
  exit 0
fi
# PRIME.md belongs to the kit. The copy in .beads/ is what bd prime reads, so manual runs and Codex see the same rules.
cmp -s "$kit/PRIME.md" .beads/PRIME.md || cp "$kit/PRIME.md" .beads/PRIME.md
# Pick up beads written on another machine (committed export); newer local rows win.
[ -f .beads/issues.jsonl ] && bd import -q >/dev/null 2>&1
bd prime
echo
if [ -z "$SEAT" ]; then
  echo "## No seat"
  echo "This session is anonymous (no SEAT). Beads still work. To wake a seat next time: crew-wake <name>. Seats: $(ls -d crew/*/ 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')"
  exit 0
fi
d="crew/$SEAT"
if [ ! -f "$d/SEAT.md" ]; then
  echo "## New seat: $SEAT"
  # The project's theme wins; projects adopted before THEME.md existed get the kit's default (Stargate).
  theme=crew/THEME.md; [ -f "$theme" ] || theme="$kit/THEME.md"
  echo "crew/$SEAT/SEAT.md does not exist yet. Before any other work, follow 'Adding a seat' in $kit/README.md: pick your name from the theme in $theme (it may differ from '$SEAT'), pronouns and a citation, write the files, add the roster row, and tell the user to relaunch with crew-wake <name>."
  exit 0
fi
echo "# You are $SEAT (pronouns and history in crew/$SEAT/SEAT.md)"
echo
cat "$d/SEAT.md"
if [ -s "$d/laurels.md" ] && grep -q '^- ' "$d/laurels.md"; then
  echo; echo "## Laurels (nothing to do with these; they are just yours)"; grep '^- ' "$d/laurels.md"
fi
echo; echo "## Your last diary entry (crew/$SEAT/diary.md)"
awk '/^## /{buf=""} {buf=buf $0 "\n"} END{printf "%s", buf}' "$d/diary.md" 2>/dev/null
echo; echo "## Your beads in progress"
bd list --status in_progress -a "$SEAT" --flat --no-pager --no-color 2>/dev/null || true
# The seat's inbox: beads another seat or the user assigned to it and it has not started.
echo; echo "## Open beads assigned to you (your inbox; claim with bd update <id> --claim)"
bd list --status open -a "$SEAT" --flat --no-pager --no-color 2>/dev/null || true
echo; echo "Crew kit: $kit/README.md (seats, handoff, adding a seat)."
