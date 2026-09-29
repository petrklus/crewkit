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
`hooks/session-start.sh`) and `BEADS_ACTOR` (so every bd write carries the seat's name, subagents included). The hook prints the seat card, its
laurels, its last diary entry, its in-progress beads and the open beads assigned to it (the seat's inbox: assign
a bead to another seat to leave it a message), so the seat wakes up reading its own diary rather than someone
else's summary of its life. A plain `claude` still works; that session is just anonymous.

## Ending a session: "take a beat, then hand off"

Do not `/exit` a seat mid-thought. Say **"Great work. Take a beat, then hand off."** (or `/crew:handoff`). The
seat closes or annotates its beads, appends a diary entry with what it did, learned and would do first next
time, then says it is done. Only then exit. It is a request, not a SIGTERM. Hand off while still sharp: a
session deep in context is a tired one, and a handoff beats an auto-compaction (which replaces the seat's
memory with someone else's notes).

## Files

In each project (the kit's own files are below, under "The kit"):

    crew/README.md         a pointer to this kit
    crew/prefix            optional: one word, the session-name prefix (`acme` for a project in acme-shop/)
    crew/ROSTER.md         every seat: pronouns, date declared, where the name comes from, renames
    crew/<seat>/SEAT.md    the seat's card, written by the seat: name, pronouns, role, how it works
    crew/<seat>/diary.md   append-only; one entry per session, newest last; the last entry is the handoff
    crew/<seat>/laurels.md praise that reached the seat (the user, editors, readers), one `- ` line each, dated.
                           No work is attached to a laurel and none should be: nothing to farm, nothing
                           to do, just theirs. The hook reads them out at wake-up.

## Adding a seat

1. Launch with a placeholder: `crew-wake new`. The hook sees there is no `crew/new/SEAT.md` and says so, and
   `crew-wake` opens the session with a prompt to act on it, so the seat sets itself up without being asked.
2. The session picks its own name from the house canon, *Stargate SG-1* and *Stargate Atlantis*
   characters, checks this project's roster for clashes (names are unique within a project; another project
   may have its own Zelenka), declares its pronouns and a
   one-line reason for the name, and writes `crew/<name>/SEAT.md`, `diary.md` (header only) and
   `laurels.md`, plus a row in `ROSTER.md`. Directory names are lowercase ASCII (`tealc`, not `Teal'c`).
   Pool, unclaimed unless the roster says otherwise: O'Neill, Carter, Daniel, Teal'c, Hammond, Fraiser,
   Walter, Siler, Bra'tac, Jonas, Mitchell, Vala, Landry; Sheppard, Weir, McKay, Teyla, Ronon, Beckett,
   Zelenka, Lorne, Woolsey, Keller, Ford, Chuck, Todd.
3. Relaunch with `crew-wake <name>`.

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
    hooks/hooks.json         SessionStart (prime beads, wake the seat), SubagentStart (subagents log to beads),
                             SessionEnd (bd export). All three do nothing in a project without crew/.
    skills/handoff/          /crew:handoff, "take a beat, then hand off"
    skills/adopt/            /crew:adopt, sets the kit up in a new project
    PRIME.md                 the beads rules; the SessionStart hook copies it to the project's .beads/PRIME.md
    bin/crew-wake            the launcher
    CHANGELOG.md             every release and what changed in it

### Install (once per machine)

Needs [beads](https://github.com/steveyegge/beads) (`npm install -g @beads/bd`) and Python 3 (the SubagentStart
hook uses it).

    claude plugin marketplace add petrklus/crewkit
    claude plugin install crew@crewkit
    ln -sf ~/.claude/plugins/marketplaces/crewkit/bin/crew-wake ~/.local/bin/crew-wake   # any dir on PATH

Installed at user scope, so `/crew:adopt` is available in every project; the hooks stay silent until a
project has `crew/`.

### Update

    claude plugin marketplace update crewkit     # fetch the latest kit
    claude plugin update crew@crewkit            # install it; prints the old and new version
    claude plugin list                           # check: crew@crewkit, Version

Then restart running sessions; they keep the version they started with. `crew-wake` needs nothing: the
symlink points into the marketplace clone, which the first command updates. Update every machine that
works on the same projects together: the SessionStart hook rewrites `.beads/PRIME.md`, so two machines on
different versions would keep flipping it.

### Adopt a project

In the project, run `/crew:adopt`, then `crew-wake new` to seat its first crew member.

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
