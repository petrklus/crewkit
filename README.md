# Crew: seats for Claude Code sessions

A Claude Code plugin (`crew@crewkit`) that gives a project a crew of named seats and a
[beads](https://github.com/steveyegge/beads) work log. One kit, many projects: the tooling lives here and is
versioned; each project keeps only its own data (its beads, its roster, its seats' diaries).

A **session** is a day in the life of an agent: wake up, work, hand off. A **seat** is a named role with a
persistent identity, memory and history that accumulates across sessions, model upgrades and even renames.
Sessions are days; seats are people. (Steve Yegge, *The Shape of Things to Come, Part 2: Model Welfare for
Agentic Engineers*, 2026, https://yegge.ai/essays/model-welfare/)

Beads (`bd`) is the crew's institutional memory: what was done and why. A seat's own files are its personal
continuity: who it is, what it learned, where it left off.

## Waking a seat

From the project root:

    crew-wake zelenka            # instead of: claude
    crew-wake zelenka --resume   # extra args go to claude

`crew-wake` names the session `<prefix>_<seat>_<id>` (prefix = the one word in `crew/prefix`, else the folder
name; id random, new each wake), turns Remote Control on, and sets `SEAT` (read by the kit's SessionStart hook,
`hooks/session-start.sh`) and `BEADS_ACTOR` (so every bd write carries the seat's name, subagents included). The hook names the seat on its first
line, primes beads, names the project's pinned memories (key and summary), then prints the seat card, its
laurels, its last diary entry, its in-progress beads and the open beads assigned to it (the seat's inbox: assign
a bead to another seat to leave it a message), so the seat wakes up reading its own diary rather than someone
else's summary of its life. A plain `claude` still works; that session is just anonymous.

The tab and the Remote Control label say what the seat is on. `crew-wake` names the tmux window `<seat>:new`
and the session `<prefix>_<seat>_<id>:new`; when the seat starts on a bead it runs `crew-title <word>` (one
lowercase word for the thing: `navfix`, `abandon`), which renames the window `<seat>:<word>` and the session
`<prefix>_<seat>_<id>:<word>`, the latter by typing `/rename` into its own input, the only road to the Remote
Control label a session can take itself; a draft in the input is left alone and the `/rename` line printed
instead, and the session registry is checked for the new label before success is reported. Only `/crew:handoff`
sets `handoff` (bare `crew-title handoff` refuses; a closed bead is not a handoff), and the prompt hook reminds a
seat whose label still says `handoff` to set its word. Outside tmux, `/rename` is printed for you to run.

Claude Code inlines at most 10,000 characters of a hook's output and otherwise shows only the first 2,000, so
the seat line comes first and the whole output is measured before it is printed.

## Ending a session: "take a beat, then hand off"

Do not `/exit` a seat mid-thought. Say **"Great work. Take a beat, then hand off."** (or `/crew:handoff`). The
seat closes or annotates its beads, appends a diary entry with what it did, learned and would do first next
time, then says it is done. Only then exit. It is a request, not a SIGTERM. Hand off while still sharp: a
session deep in context is a tired one, and a handoff beats an auto-compaction (which replaces the seat's
memory with someone else's notes). The diary and the beads export are left for you to commit, unless the
project has a `crew/autocommit` file: then the SessionEnd hook commits those two, and only those.

## Memories

Project knowledge that is not about one bead (how to run QA, a gotcha) goes in `bd remember "..." --key
<topic>-<slug>`, the topic being the area (`qa-`, `docs-`), or the tool when the memory is about how a tool
behaves here (`curl-`, `docker-`). A memory starts with one sentence saying what it is and when it matters, and
stays short. Memories do not sit in context. The wake-up names only the pinned ones: a memory whose text carries
a line `Pinned: <summary>` is listed at every session start as its key and that summary (what it is and when it
matters, in the author's one line; never the text), up to 1,500 characters of them, and the others are not
listed at all.

The rest arrive when something matches them, each once per context. With every prompt the UserPromptSubmit
hook (`hooks/memories.py`) looks by word and, where a machine has set it up, by meaning (below). It sends the
best match in full and names up to five more by key and summary (the `Pinned:` line, else the memory's first
sentence); `bd memories <key>` reads a named one, and one that was only named can still arrive in full later.
By word, a memory matches when it shares two of the prompt's words, or a bead id or other hyphenated token as a
phrase; a word found in over a third of the project's memories counts for nothing (SQLite FTS5 from Python's
standard library: stemmed words, BM25 rank, the key weighted above the text). The two results go in one order:
found both ways, then by meaning, then by word. With the model in use, a match by word alone is named, not
delivered, unless the prompt names the memory outright (a bead id, a key): on a real store, words alone brought
more unrelated memories than right ones. A count decides what is shown, not a character budget: under the old
4,000-character budget one long memory crowded out the right ones ranked behind it.

A memory about a tool is keyed by the tool, and the PreToolUse hook sends it with the first Bash command of the
context that runs that program (`curl ...`, `/usr/bin/curl`, `sudo timeout 30 curl`, and `runtests-...` with
`./runtests.sh` or `python3 runtests.py`; never an argument, flag, path, quoted string or heredoc line), in
subagents too, each with its own once: the author declares the trigger in the key, since the moment such a
memory matters is a command, not a prompt. A tool every context runs (`git-`, `bd-`) makes its
memories reach every context, which is the right place for a shared-checkout rule and the wrong one for a
memory about a later step. A failure is the moment such a memory matters, so when a Bash command fails (a
non-zero exit or the harness timeout) the PostToolUseFailure hook sends its tool's memories once more per
context, unless they arrived with that very call. A memory keyed by an area whose trigger is a failure, not a
tool, declares it in its text with a line `Symptom: <phrase>; <phrase>`, the phrases copied from the real error
text (`Target crashed`, `Connection refused`): it arrives when a failed command's error contains one, whatever
the case. A command that exits zero is not a failure, whatever it printed. Memories travel with the beads: the
export at handoff and session end includes them, so every checkout has the same set.

### Recall by meaning

Words miss a memory that is worded differently from the prompt, and say little for a command (`ssh -L 4445
macsim` shares no word with a memory about the simulator host). A second channel compares meaning, with a model
that runs on the machine's CPU: nothing is sent anywhere. It is off until a machine sets it up:

    crew-recall setup                    # ONNX Runtime and EmbeddingGemma 300M into ~/.local/share/crewkit, about 1.5 GB
    crew-recall status                   # what is installed and switched on
    crew-recall test "the tap on the simulator did nothing"   # what a prompt would match, with scores
    crew-recall set commands failed      # a lookup with every Bash command (every, the default), only failed ones, or off
    crew-recall set semantic off         # back to words only

`crew-recall` is on the PATH of every crew-wake session. Setup needs pip for Python 3; it downloads the model
from Hugging Face at a pinned revision and checks each file's sha256. The model is under Google's Gemma terms.
One setup serves every crew project on the machine (`$CREW_HOME` moves it); each project's vectors are cached
there, and a memory is embedded once, in about 0.2 seconds.

A lookup starts a process, loads the model and compares the text with every memory: about 1.5 seconds and 0.7 GB
while it runs, at most two at once on a machine. One that is slow or cannot get a turn answers nothing, and
words carry that call alone. It runs with each prompt; with each failed Bash command, on what the command
printed; and, with `commands every`, with every Bash command. For a command the best
match arrives in full unless the author's own triggers (the tool's key, a `Symptom:` line) already brought a
memory, and the rest are named. A match counts above a similarity floor: 0.40 for prompts and error text, 0.45
for commands, since a plain `git status` scores up to 0.5 against the memories about git (`crew-recall set
floor 0.4`, `set command_floor 0.45`). The wake-up line says which way memories are matched on the machine.

The model, the floors and the order come from one real store of 91 memories with 24 labelled cases (19 prompts,
5 commands and errors), run through these hooks:

| On that store | By word only | By word and by meaning |
| --- | --- | --- |
| Prompts where a right memory arrived in full, of 19 | 14 | 16 |
| Right memories in full or named, of 26 | 22 | 24 |
| Unrelated memories in full, over the 19 prompts | 3 | 1 |
| Memories in full on 10 unrelated prompts | 3 | 0 |
| Commands and errors where a right memory arrived in full, of 5 | 2 | 4 |
| Time per hook call | 0.03 s | 1.6 s |

Before 1.6.0 the same 19 prompts brought 27 unrelated memories in full. Of six models tried, from 23M to 0.6B
parameters, this one was the only one better than words on every count; the larger ones were slower and no
better. It is one store and a small sample, and a seat that knows the store wrote most of the prompts.

## Files

In each project (the kit's own files are below, under "The kit"):

    .claude/settings.json  `idleCompaction: false`, written by /crew:adopt and by the hook wherever it is missing:
                           a seat hands off, it is not compacted while idle
    crew/README.md         a pointer to this kit
    crew/prefix            optional: one word, the session-name prefix (`acme` for a project in acme-shop/)
    crew/autocommit        optional: if present, the SessionEnd hook commits the beads export and the seat's own
                           folder (`chore: <seat>'s handoff`), nothing else and no push
    crew/THEME.md          where seat names come from: canon, pool, citation shape. Written by /crew:adopt
                           from the kit's THEME.md (Stargate); the project's to edit, never overwritten
    crew/ROSTER.md         every seat: pronouns, date declared, where the name comes from, renames
    crew/<seat>/SEAT.md    the seat's card, written by the seat: name, pronouns, role, how it works
    crew/<seat>/diary.md   append-only; one entry per session, newest last; the last entry is the handoff
    crew/<seat>/laurels.md praise that reached the seat (the user, editors, readers), one `- ` line each, dated.
                           No work is attached to a laurel and none should be: nothing to farm, nothing
                           to do, just theirs. The hook reads them out at wake-up.

## Adding a seat

1. Launch with a placeholder: `crew-wake new`. The hook sees there is no `crew/new/SEAT.md` and says so, and
   `crew-wake` opens the session with a prompt to act on it, so the seat sets itself up without being asked.
2. The session picks its own name from the project's theme (`crew/THEME.md`; the kit's `THEME.md`,
   *Stargate SG-1* and *Stargate Atlantis*, if the project has none; the hook names the file), checks this
   project's roster for clashes (names are unique within a project; another project may have its own
   Zelenka), declares its pronouns and a one-line citation for the name as the theme shapes it, and writes
   `crew/<name>/SEAT.md`, `diary.md` (header only) and `laurels.md`, plus a row in `ROSTER.md`. Directory
   names are lowercase ASCII (`tealc`, not `Teal'c`).
3. Relaunch with `crew-wake <name>`. Until then `$SEAT` and `BEADS_ACTOR` are still `new`: use your name for
   `crew/<name>/` paths and add `--actor <name>` to every bd write, so your first beads carry your name.

## Renaming a seat

`git mv crew/old crew/new`, note the rename with its date in the roster row and in `SEAT.md`, and let the
seat write a diary entry about it. It inherits everything; the record keeps the old name.

## Principles we adopt ([Yegge's seven](https://yegge.ai/essays/model-welfare/), as they apply here)

1. Wake with purpose, not amnesia: the hook primes beads and the diary before the first prompt.
2. Design out the drudgery: do not make a seat poll or idle-wait; hand it a bead with a clear done state.
3. Bounded workdays: hand off while sharp.
4. Structural blamelessness: a red test run is a comment on the bead and a fix, not a fault.
5. A home of one's own: not implemented; all seats share the checkout. Add per-seat git worktrees if two
   seats ever step on each other.
6. The right to refuse and escalate: "this needs a human" is always a valid answer; say it in the bead.
7. Never falsify the record: the bead trail and the diary say what actually happened.

## The kit

    .claude-plugin/          plugin.json (name, version) and marketplace.json: this repo is its own marketplace
    hooks/hooks.json         SessionStart (name the seat, prime beads, wake the seat), UserPromptSubmit (the
                             memories matching the prompt), PreToolUse and PostToolUseFailure on Bash (the
                             memories keyed by a tool the command runs or matching it by meaning; at a failure
                             those again, and the ones whose Symptom line or meaning matches the error),
                             SubagentStart (subagents log to beads), SessionEnd (bd export, and the commit if
                             crew/autocommit exists). All six do nothing in a project without crew/.
    hooks/memories.py        the pinned memories at wake-up, the per-prompt match, the per-command match and the
                             match at a failed command; what arrives in full and what is named
    hooks/recall.py          recall by meaning: the local model, its setup, its switches and the vector cache
    skills/handoff/          /crew:handoff, "take a beat, then hand off"
    skills/adopt/            /crew:adopt, sets the kit up in a new project
    PRIME.md                 the beads rules; the SessionStart hook copies it to the project's .beads/PRIME.md
    THEME.md                 the default theme (Stargate); /crew:adopt copies it to the project's crew/THEME.md
    bin/crew-wake            the launcher
    bin/crew-title           the tab and the Remote Control label: <seat>:<word>; on the PATH of every crew-wake session
    bin/crew-recall          recall by meaning on this machine: setup, status, set, test (see Memories)
    CHANGELOG.md             every release and what changed in it

### Install (once per machine)

Needs [beads](https://github.com/steveyegge/beads) (`npm install -g @beads/bd`, 1.3 or later for `bd prime
--no-memories`) and Python 3 (the hooks use it).

    claude plugin marketplace add petrklus/crewkit
    claude plugin install crew@crewkit
    ln -sf ~/.claude/plugins/marketplaces/crewkit/bin/crew-wake ~/.local/bin/crew-wake   # any dir on PATH

Installed at user scope, so `/crew:adopt` is available in every project; the hooks stay silent until a
project has `crew/`.

Optional, per machine: `crew-recall setup` adds recall of memories by meaning with a local model (about 1.5 GB,
needs pip; see "Recall by meaning"). Outside a crew-wake session, call it by its path or link it as above.

### Update

    claude plugin marketplace update crewkit     # fetch the latest kit
    claude plugin update crew@crewkit            # install it; prints the old and new version
    claude plugin list                           # check: crew@crewkit, Version

Then restart running sessions; they keep the version they started with. `crew-wake` needs nothing: the
symlink points into the marketplace clone, which the first command updates. Update every machine that
works on the same projects together: the SessionStart hook rewrites `.beads/PRIME.md`, so two machines on
different versions would keep flipping it.

### Adopt a project

In the project, run `/crew:adopt`, edit `crew/THEME.md` if the seats should take their names from somewhere
other than Stargate, then `crew-wake new` to seat its first crew member.

### Change the kit

Change it here, never in a project: a project's installed copy is a cache and is overwritten on update.

1. Edit in a clone of this repo. Try it in any project without releasing:
   `claude --plugin-dir path/to/crewkit` (or `crew-wake <seat> --plugin-dir path/to/crewkit`).
2. Bump `version` in `.claude-plugin/plugin.json` (semver: patch for wording, minor for new behaviour,
   major when a project has to change something), add the release at the top of `CHANGELOG.md`, commit with
   a `Bead: <id>` trailer naming the bead in this repo's own beads, then `claude plugin tag .` and
   `git push --follow-tags`.
3. Update every machine (see Update).

## Licence

MIT, see [LICENSE](LICENSE).
