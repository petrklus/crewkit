#!/bin/sh
# PreToolUse hook (Bash): the memories (bd remember) whose key topic names a tool the command runs arrive with its
# result, once per context (ck-7d3). Fires in subagents too; they get their own once.
# PostToolUseFailure hook (Bash), same script: a failed command (non-zero exit, harness timeout) brings its tool's
# memories once more, and the ones whose 'Symptom:' line has a phrase found in the error text.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if [ ! -d crew ] || ! command -v bd >/dev/null 2>&1; then cat >/dev/null; exit 0; fi
# ponytail: bd memories --json before every Bash call (0.15 s) and after a failed one; cache the JSON per session if it shows.
exec python3 -I "$(dirname "$0")/memories.py" tool
