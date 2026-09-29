#!/bin/sh
# SubagentStart hook: every spawned agent contributes to beads on behalf of the seat that spawned it.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
cat >/dev/null
[ -d crew ] || exit 0
command -v bd >/dev/null 2>&1 || exit 0
wip=$(bd list --status in_progress --flat --no-pager --no-color 2>/dev/null | head -20)
python3 - "${SEAT:-no seat}" "$wip" <<'PY'
import json, sys
seat, wip = sys.argv[1], sys.argv[2]
ctx = f"""## Beads (the work log)
You are a subagent working for seat '{seat}' in a beads (bd) workspace. The lead session names the bead id you serve; if it did not, use the one in progress below and say so in your report.
- Record every finding that changes the plan, in the bead: bd comment <id> "what you found and why it matters".
- Follow-up work you discover but do not do: bd create "Title" -t task -d "why it is needed" --deps discovered-from:<id>
- Never close, claim or reassign a bead; the lead does that. No TodoWrite or markdown TODO lists.
In progress now:
{wip or '(none)'}"""
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": ctx}}))
PY
