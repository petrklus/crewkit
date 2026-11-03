#!/bin/sh
# UserPromptSubmit hook: the memories (bd remember) that share words with the prompt arrive with it (ck-6l5).
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if [ ! -d crew ] || ! command -v bd >/dev/null 2>&1; then cat >/dev/null; exit 0; fi
# A label still saying handoff when a prompt arrives: the seat kept working after a handoff, or set it by reflex
# (ck-hy9). Say so once per prompt; the seat picks the word.
[ -n "$CREW_SESSION" ] && python3 -I - "$CREW_SESSION" <<'PY' 2>/dev/null
import glob, json, os, sys
d = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
for f in glob.glob(d + "/sessions/*.json"):
    try: name = json.load(open(f)).get("name", "")
    except Exception: continue
    if name == sys.argv[1] + ":handoff":
        print("## Title\nYour label still says handoff and a prompt has arrived: once you know what you are on, run crew-title <word>.\n")
PY
exec python3 -I "$(dirname "$0")/memories.py" match
