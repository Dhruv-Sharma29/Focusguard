# FocusGuard — Architecture

This document explains how FocusGuard is structured internally: module responsibilities, data flow, and the reasoning behind key design decisions. It's aimed at contributors and anyone auditing the code for privacy/security claims.

---

## Design principles

Four rules shape every decision in this codebase:

1. **Local-first, always.** No data leaves the machine unless the user explicitly triggers an AI coach command. There is no telemetry, no analytics, no phone-home behavior.
2. **Encrypted at rest.** The activity database is encrypted. A stolen laptop should not expose someone's productivity history.
3. **Minimal AI context.** When AI coaching is enabled, only the current goal and elapsed stuck-time are sent — never the full activity log or browsing history.
4. **Auditable by design.** Every module that touches sensitive data (window titles, tokens, the database) is small and isolated, so it's easy for a reviewer to verify what it actually does.

---

## Module map

```
src/focusguard/
├── commands/        CLI command handlers (one file per command group)
├── core/             Shared business logic: focus scoring, polling loop
├── db/               SQLite access layer (encrypted)
├── integrations/     External systems: git, GitHub API, LLM providers
├── personality/      Message templates and tone per personality mode
├── platform/         OS-specific window detection + daemon installation
├── security/         Encryption, keyring access, sensitive-site blocklist
├── ui/               Rich-based terminal rendering
├── __main__.py        Entry point for `python -m focusguard`
├── config.py          Loads and validates config.toml
└── main.py            Typer app assembly — registers all commands
```

---

## Data flow: the core tracking loop

This is the heart of the application. Everything else is built around it.

```
                    ┌─────────────────────┐
                    │  platform/window.py  │
                    │  Active window poll  │
                    └──────────┬───────────┘
                                │ every 60s
                                ▼
                    ┌─────────────────────┐
                    │ security/blocklist.py│
                    │  Redact sensitive    │
                    │  window titles       │
                    └──────────┬───────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │  core/ (scoring)     │
                    │  Classify activity   │
                    │  Update focus score  │
                    └──────────┬───────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │  db/connection.py    │
                    │  Write to encrypted  │
                    │  SQLite (via crypto) │
                    └──────────────────────┘
```

Nothing in this loop touches the network. The blocklist check happens **before** anything is written to disk — a sensitive window title is never persisted, even encrypted, if it matches a blocklist pattern.

---

## Module responsibilities

### `commands/`
One file per command group (`start.py`, `stop.py`, `goal.py`, `coach.py`, `daemon.py`, `github_cmd.py`, `report.py`, `stats.py`, `privacy.py`). Each file defines its Typer subcommands and calls into `core/`, `db/`, or `integrations/` — command files should contain argument parsing and output formatting only, not business logic. This keeps the CLI surface easy to scan independently of how features are implemented.

### `core/`
The focus-scoring algorithm, the procrastination pattern-detection engine (weighted signals, see README), and the 60-second polling loop live here. This module also handles **tab-level app classification**, using prioritized window titles to intelligently classify tabs (e.g., recognizing "LeetCode" in Safari as coding rather than generic browser time). This is the only module every command ultimately depends on.

### `db/`
- `connection.py` — opens the encrypted SQLite connection, handles the encryption key handoff from `security/crypto.py`
- `models.py` — table schemas (`users`, `goals`, `activity_log`, `focus_scores`, `reports`)
- `queries.py` — all SQL lives here, nowhere else. No other module should write raw SQL — this makes the data layer the single place to audit for injection risk or query correctness.

### `integrations/`
- `git_tracker.py` — local repo commit scanning via GitPython
- `github_api.py` — remote GitHub API calls (commits, PRs, issues) using the keyring-stored token
- `llm.py` — the AI coach backend abstraction. Builds the minimal context payload and routes to either Ollama or OpenAI depending on config. This is the only file in the codebase that should ever construct a network request containing user activity data, and it should only do so on an explicit `coach` command — never from the background daemon loop.

### `personality/`
- `modes.py` — defines the four modes (coach, strict, friend, roast) as configuration objects (tone, thresholds for triggering a nudge)
- `prompts.py` — template strings and, when AI is enabled, the system prompts sent to the LLM per mode

### `platform/`
OS-specific code, isolated so the rest of the app stays platform-agnostic:
- `window.py` — dispatches to the correct active-window detection method per OS
- `daemon_linux.py` / `daemon_macos.py` / `daemon_windows.py` — generate and install the systemd unit, launchd plist, or Task Scheduler entry respectively

This is deliberately the most fragmented part of the codebase, because active-window detection and background persistence are the two areas with no cross-platform abstraction in the Python ecosystem — each OS needs its own implementation.

### `security/`
- `crypto.py` — wraps the encryption library (SQLCipher or `cryptography`), handles key derivation
- `keyring_store.py` — the only module permitted to call `python-keyring`. GitHub tokens, OpenAI keys, and the DB encryption key all go through here
- `blocklist.py` — checks window titles against the user's sensitive-site patterns before anything reaches `db/`

### `ui/`
Rich-based rendering for `report`, `stats`, and `daemon status` output. Pure presentation — takes data structures in, renders terminal output, no business logic.

---

## Why these specific design decisions

**Why is the blocklist check in `security/` instead of `platform/window.py`?**
Keeping it as a separate, single-purpose module means it's the one file a security-conscious contributor needs to read to verify what's filtered before storage — it isn't buried inside OS-specific window-polling code.

**Why does `integrations/llm.py` build its own minimal context rather than receiving the full activity object?**
This is a deliberate API boundary, not just a convention. The function signature for sending data to an LLM provider should make it structurally difficult to accidentally pass the whole database — the context payload is built explicitly field-by-field (goal text, stuck-time minutes) rather than serializing an existing object.

**Why SQLite with application-level encryption instead of a server-based DB?**
Rule #1 is local-first. A server, even a local one, adds an attack surface (a listening port) and an operational dependency (something that can crash and needs restarting) for no benefit to a single-user tool.

**Why is the daemon installer per-OS rather than using a cross-platform library?**
Existing cross-platform "run on startup" libraries tend to lowest-common-denominator their way around real OS differences (permission models, logging conventions, restart-on-crash behavior). Writing the systemd/launchd/Task Scheduler integration directly gives more control and makes failures easier to diagnose per-platform.

---

## Database schema (high level)

| Table | Purpose |
|---|---|
| `users` | Single local user profile, settings snapshot |
| `goals` | User-created goals: text, status, created/completed timestamps |
| `activity_log` | Raw per-poll records: app name, sanitized window title, category, timestamp |
| `focus_scores` | Computed daily/hourly scores, derived from `activity_log` |
| `reports` | Cached report data for fast `report`/`stats` rendering |

`activity_log` is the only table subject to the retention policy — rows older than `retention_days` (default 90) are aggregated into `focus_scores` and then deleted. `goals` and `focus_scores` are kept indefinitely since they're small and useful for long-term trend views.

---

## Extending FocusGuard

If you're adding a feature, here's where it likely belongs:

- **New CLI command** → new file in `commands/`, thin wrapper calling into `core/` or `integrations/`
- **New procrastination signal** → `core/` scoring engine, add a weighted signal per the existing pattern
- **New LLM provider** → `integrations/llm.py`, add a new branch in the provider dispatch
- **New personality mode** → `personality/modes.py` + corresponding templates in `prompts.py`
- **New platform support** → new `platform/daemon_<os>.py`, register it in the daemon dispatch logic

Anything that reads window titles, stores credentials, or sends data over the network should go through `security/` or the existing `integrations/llm.py` boundary — don't create a second path that bypasses the blocklist or the keyring.
