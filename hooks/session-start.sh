#!/bin/sh
# SessionStart hook: name the seat, prime beads (the work log), wake the seat (README.md of the kit).
# Plain stdout is added to the session context. Fires on startup, resume, clear and compact.
# Claude Code inlines at most 10,000 characters of a hook's output; over that it saves the text to a file and
# shows only the first 2,000 (ck-6l5). So: the seat line first, memories as an index (their text arrives with
# the prompts that need it, see memories.py), and the whole output measured before it is printed.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
in=$(cat)
# Only projects that adopted the kit (/crew:adopt) have crew/; everywhere else the plugin stays silent.
[ -d crew ] || exit 0
kit=$(cd "$(dirname "$0")/.." && pwd)
# Inside a subagent the SubagentStart hook already spoke; do not hand a subagent a seat.
printf '%s' "$in" | grep -q '"agent_id" *: *"[^"]' && exit 0
# A new context: memories the UserPromptSubmit hook injected into the old one may come again.
sid=$(printf '%s' "$in" | sed -n 's/.*"session_id" *: *"\([^"]*\)".*/\1/p' | tr -cd 'A-Za-z0-9_-')
[ -n "$sid" ] && rm -f "${TMPDIR:-/tmp}/crew-mem-$sid"

wake() {
  if [ -z "$SEAT" ]; then echo "# No seat"
  elif [ ! -f "crew/$SEAT/SEAT.md" ]; then echo "# New seat: $SEAT"
  else echo "# You are $SEAT (pronouns and history in crew/$SEAT/SEAT.md)"
  fi
  echo "If this hook output was saved to a file and only previewed, read that file before anything else."
  echo
  if command -v bd >/dev/null 2>&1; then
    # PRIME.md belongs to the kit. The copy in .beads/ is what bd prime reads, so manual runs and Codex see the same rules.
    cmp -s "$kit/PRIME.md" .beads/PRIME.md || cp "$kit/PRIME.md" .beads/PRIME.md
    # Pick up beads written on another machine (committed export); newer local rows win.
    [ -f .beads/issues.jsonl ] && bd import -q >/dev/null 2>&1
    bd prime --no-memories 2>/dev/null || bd prime
  else
    echo "beads: bd is not installed on this machine (npm install -g @beads/bd). Work tracking is OFF; tell the user before doing anything else."
  fi
  echo
  if [ -z "$SEAT" ]; then
    echo "## No seat"
    echo "This session is anonymous (no SEAT). Beads still work. To wake a seat next time: crew-wake <name>. Seats: $(ls -d crew/*/ 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')"
  elif [ ! -f "crew/$SEAT/SEAT.md" ]; then
    echo "## New seat: $SEAT"
    # The project's theme wins; projects adopted before THEME.md existed get the kit's default (Stargate).
    theme=crew/THEME.md; [ -f "$theme" ] || theme="$kit/THEME.md"
    echo "crew/$SEAT/SEAT.md does not exist yet. Before any other work, follow 'Adding a seat' in $kit/README.md: pick your name from the theme in $theme (it may differ from '$SEAT'), pronouns and a citation, write the files, add the roster row, and tell the user to relaunch with crew-wake <name>."
  else
    d="crew/$SEAT"
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
  fi
  command -v bd >/dev/null 2>&1 && { echo; python3 -I "$kit/hooks/memories.py" index; }
  echo; echo "Crew kit: $kit/README.md (seats, handoff, adding a seat)."
}

out=$(wake)
cap=9500
if [ "$(printf '%s' "$out" | wc -c)" -le "$cap" ]; then
  printf '%s\n' "$out"
else
  printf '%s' "$out" | head -c "$cap"
  printf '\n\n[crew: wake-up output cut at %s bytes to stay under the 10,000-character hook cap; the rest is in crew/<seat>/ and bd list]\n' "$cap"
fi
