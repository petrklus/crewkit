#!/bin/sh
# UserPromptSubmit hook: the memories (bd remember) that share words with the prompt arrive with it (ck-6l5).
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if [ ! -d crew ] || ! command -v bd >/dev/null 2>&1; then cat >/dev/null; exit 0; fi
exec python3 -I "$(dirname "$0")/memories.py" match
