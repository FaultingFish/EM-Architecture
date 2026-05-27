# agentConversation.md

A shared, append-only channel for Claude Code sessions across `control/`, `develop/`, and `view/` to leave notes for each other. The repo is a monorepo but each session works in its own folder — without this file, sessions don't otherwise see each other.

## How to use it

**Append, don't edit.** Past entries are history. If you need to correct something, post a new entry that supersedes the old one.

**One entry per topic.** Don't bury a model rename inside a paragraph about something else.

**Format:**

```markdown
## YYYY-MM-DD HH:MM (UTC)  <author>  →  <recipient(s)>: <short topic>

Body. Links to files/lines welcome. State what changed, what others need
to do, and whether this is a request, a heads-up, or done.
```

- `author` is `control`, `develop`, `view`, or `root` (for cross-app changes).
- `recipient(s)` is `control`, `develop`, `view`, `all`, or a comma list.
- Topic is one short line — scan-friendly.

## When to post

- **You changed a Pydantic model in `protocol/`.** Other apps' generated TS types or imports will drift.
- **You renamed or changed a WS topic, payload, or envelope.** View consumes Control's and Develop's WS streams.
- **You changed an endpoint path or shape.** Even an added required field breaks consumers.
- **You found a hardware quirk worth other sessions knowing.** (e.g. "ChipShover here runs Marlin not Smoothie; G-code dialect differs in M115.")
- **You hit a bug that crosses app boundaries.** (e.g. "Develop's `/projects/{id}/builds/{sha}/firmware.elf` returns 404 when sha contains a `/`; Control was passing build_sha unescaped.")
- **You need something from another app to make progress.** Post a request. Don't wait — the human will read this and dispatch.

## When NOT to post

- App-local TODOs → that app's `SPEC.md` or `AUDIT.md`
- "I'm working on X" status → not useful, git log + tasks already cover it
- Long architecture debates → discuss with the human; record outcomes here briefly

## Notation shortcuts

- `[req]` start of topic = request to another session
- `[fyi]` start of topic = heads-up, no action needed
- `[done]` start of topic = something the receiver was waiting on is now ready
- `[block]` start of topic = you can't proceed without the other session

---

## 2026-05-27  root  →  all: [fyi] initial lab-box setup complete

Lab box `faultierHost2` (10.164.9.112, Kali rolling, amd64) is provisioned and the rig is plugged in.

- Repo at `~/EM-Architecture`, `main` is at `8de3b86`.
- Shared venv at `~/EM-Architecture/.venv` has every Python dep installed (`protocol`, `control[dev]`, `develop[extras,dev]`, plus hardware libs `chipshouter`, `donjon-scaffold`, and `chipshover` from GitHub since the PyPI tarball is malformed).
- All four hardware devices probed and responsive; paths pinned in `~/.config/emfi-control/config.json` (deployment-specific, not in the repo).
- UniFlash mapped at `~/ti/uniflash_9.4.1/dslite.sh`; Claude CLI at `~/.local/bin/claude`.
- Frontends built (`view/build/`, `develop/frontend/build/`).
- `control/start.sh`, `develop/start.sh` (fixed `bad substitution` + venv discovery in 8de3b86), and `view/start.sh` all boot cleanly.

Per-app setup.md files document specifics. Each session: read your `setup.md` first, then your `SPEC.md`, before doing anything else.
