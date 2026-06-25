# FocusGuard

**Privacy-first developer productivity tracker.** Runs locally. Zero telemetry. Your data never leaves your machine.

FocusGuard monitors which app is in focus, computes a focus score, and helps you stay productive — with optional AI coaching and a roast mode that'll make you close YouTube.

```
$ focusguard stats
  Focus: 78/100 (up)  |  Coding: 3h 42m  |  Distraction: 27m  |  Since 09:15 AM

$ focusguard roast
  Focus score: 43. You've spent more time switching tabs
  than actually working. Your IDE filed a missing persons report.
```

---

## Documentation

| | |
|---|---|
| [**Setup Guide**](docs/SETUP.md) | Full install, daemon, AI coach, and uninstall instructions |
| [**Architecture**](docs/ARCHITECTURE.md) | Module structure, data flow, and design decisions |

---

## Features

| Feature | Description |
|---------|-------------|
| **Activity tracking** | Polls active window every 60s. Tracks individual tabs (e.g. "Safari: LeetCode") |
| **Focus score** | 0–100 score with time-decay weighting (recent activity counts more) |
| **Rich dashboard** | Full terminal UI with score, timeline, breakdown, and distractions |
| **Background daemon** | Survives terminal close — launchd (macOS), systemd (Linux), Task Scheduler (Windows) |
| **Goal engine** | Set goals, track time on them, get nudged after 45 min of inactivity |
| **AI coach** | Opt-in rubber duck debugging via Ollama (local) or OpenAI (paid) |
| **GitHub integration** | Weekly commit/PR/issue summary, local repo scanning |
| **Smart procrastination detection** | Pattern-based, not "YouTube = bad" — avoids false positives for research |
| **Personality modes** | Coach, Strict, Friend, Roast |
| **Encrypted database** | SQLCipher AES-256 encryption at rest |
| **Privacy controls** | Blocklist for sensitive sites, retention policy, full uninstall |

---

## Installation

```bash
pip install focusguard
```

**With optional features:**
```bash
pip install focusguard[ai]       # AI coaching (Ollama + OpenAI)
pip install focusguard[github]   # GitHub integration
pip install focusguard[all]      # Everything
```

**From source:**
```bash
git clone https://github.com/Dhruv-Sharma29/Focusguard.git
cd focusguard

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the app
pip install -e .
```

**Alternative: install globally (no virtual environment needed)**
If you want the `focusguard` command available everywhere, use `pipx`:
```bash
brew install pipx
pipx ensurepath
pipx install .
```

### Platform notes

**macOS**: Accessibility permissions are required for window title tracking.
Go to **System Settings → Privacy & Security → Accessibility** and add your terminal app.

**Linux (Wayland)**: Window title access is restricted by design. FocusGuard works best on X11. On Wayland, only app names (not window titles) are tracked.

**Windows**: `psutil` + process monitoring may trigger Windows Defender. This is a false positive — FocusGuard only reads the active window name, never injects into processes or captures keystrokes. See [Antivirus FAQ](#antivirus-faq) below.

For full step-by-step setup, see the [Setup Guide](docs/SETUP.md).

---

## Quick Start

```bash
# Start tracking (foreground)
focusguard start

# Start as background daemon
focusguard start -d

# See your stats
focusguard stats

# Full dashboard
focusguard report

# Set a goal
focusguard goal add "Build authentication system"

# Get roasted
focusguard roast
```

---

## Commands

### Core
| Command | Description |
|---------|-------------|
| `focusguard start` | Start the tracker (foreground) |
| `focusguard start -d` | Start as background daemon |
| `focusguard stop` | Stop the tracker |
| `focusguard stats` | Quick one-line summary |
| `focusguard report` | Full Rich dashboard |
| `focusguard report -p week` | Weekly summary |

### Goals
| Command | Description |
|---------|-------------|
| `focusguard goal add "..."` | Set a new focus goal |
| `focusguard goal list` | List active goals |
| `focusguard goal complete <id>` | Mark a goal as done |
| `focusguard goal drop <id>` | Drop a goal |

### AI Coach
| Command | Description |
|---------|-------------|
| `focusguard coach help` | Ask the AI for help (opt-in) |
| `focusguard coach help -b` | Break goal into subtasks |
| `focusguard coach nudge` | Get a personality-based nudge |
| `focusguard coach mode roast` | Switch personality mode |
| `focusguard coach enable` | Enable AI coaching |
| `focusguard coach disable` | Disable AI coaching |
| `focusguard coach setup-openai` | Configure OpenAI API key |
| `focusguard roast` | Shortcut for roast mode |

### GitHub
| Command | Description |
|---------|-------------|
| `focusguard github setup` | Configure GitHub token |
| `focusguard github summary` | Weekly GitHub activity |
| `focusguard github repos ~/Code` | Scan local repos |

### Daemon
| Command | Description |
|---------|-------------|
| `focusguard daemon install` | Install OS background service |
| `focusguard daemon uninstall` | Remove background service |
| `focusguard daemon status` | Check if daemon is running |

### Privacy
| Command | Description |
|---------|-------------|
| `focusguard privacy show` | See what's tracked vs not tracked |
| `focusguard privacy blocklist` | Manage sensitive site list |
| `focusguard privacy export-key` | Backup encryption key |
| `focusguard privacy uninstall` | Full data removal |

---

## Privacy & Security

FocusGuard is designed to be auditable. It's open source, runs locally, and has **zero telemetry**.

See [Architecture](docs/ARCHITECTURE.md) for how each security boundary is implemented in code.

### What is tracked
- Active app name (e.g., "VS Code", "Chrome")
- Window title (**sanitized** — sensitive sites are redacted)
- App category and duration
- Focus score (computed locally)
- Git commits (count and messages, from local repos)

### What is NEVER tracked
- Keystrokes or typing content
- Clipboard contents
- Screenshots or screen recordings
- DMs, emails, or message content
- Passwords or authentication tokens
- Banking or healthcare site URLs
- File contents or source code
- Network traffic

### Security measures
- **Database encryption**: SQLCipher AES-256 encryption at rest
- **Secrets in OS keyring**: GitHub tokens, API keys, and the DB encryption key are stored via `python-keyring` (Keychain on macOS, Credential Manager on Windows, Secret Service on Linux) — never in config files
- **Sensitive site blocklist**: Banking, healthcare, and auth sites have their window titles replaced with `[private]`
- **Auto-deletion**: Raw activity logs older than 90 days are aggregated into daily summaries, then deleted
- **No telemetry**: No crash reporting, no analytics, no update checks, no network requests (unless you explicitly enable AI coaching)

---

## Smart Procrastination Detection

FocusGuard doesn't use naive rules like "YouTube = bad." Instead, it reads **compound patterns**:

```
goal set + 1 hour elapsed + 0 files modified + 0 git activity + 16 browser tabs
= procrastinating
```

This avoids false positives where reading documentation or watching a tutorial looks like distraction but isn't. The engine uses weighted signals:

| Signal | Weight | Triggers when |
|--------|--------|---------------|
| Goal set, no progress | 0.30 | Active goal + 0 coding in last hour |
| Excessive app switching | 0.20 | 10+ unique apps in 30 minutes |
| Long entertainment | 0.40 | 30+ min entertainment in last hour |
| Zero git activity | 0.10 | No commits + goal set 2+ hours ago |
| High distraction ratio | 0.25 | Distraction > coding in last hour |
| Known slump hour | 0.10 | Current hour is historically unproductive |

Procrastination alert triggers when the weighted sum exceeds **0.6**.

---

## Personality Modes

| Mode | Command | Vibe |
|------|---------|------|
| **Coach** | `focusguard coach nudge` | "80% done. One more problem. You've got this." |
| **Strict** | `focusguard coach mode strict` | "42 min YouTube. Not in today's plan." |
| **Friend** | `focusguard coach mode friend` | "Hey, you've been at this a while. Take a break?" |
| **Roast** | `focusguard roast` | "You opened LeetCode 7 times. Solved 1 problem. The problem wasn't LeetCode." |

---

## Configuration

Config file: `~/.config/focusguard/config.toml` (optional — all settings have defaults)

```toml
[tracker]
poll_interval = 60        # seconds between polls
idle_threshold = 300      # seconds before marking idle

[security]
blocklist = ["chase.com", "healthcare", "private"]
retention_days = 90       # auto-delete raw logs older than this

[personality]
mode = "coach"            # coach, strict, friend, roast

[ai]
enabled = false
provider = "ollama"       # ollama or openai
ollama_model = "llama3.2:3b"  # runs on 6GB+ RAM
```

Full reference and platform-specific config paths: [Setup Guide, Part 9](docs/SETUP.md#part-9-configuration-reference).

---

## <a name="antivirus-faq"></a>Antivirus FAQ

**Q: Why does Windows Defender flag FocusGuard?**

A: FocusGuard uses `psutil` to check process information and `PyWinCtl` to read window titles. These are standard Python libraries, but some antivirus software flags any process that reads window information. FocusGuard does NOT:
- Inject code into other processes
- Capture keystrokes or input
- Record screen content
- Modify system files
- Make network requests (unless AI coaching is explicitly enabled)

You can audit every line of code — it's open source.

---

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/Dhruv-Sharma29/Focusguard.git
cd focusguard
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/

# Type check
mypy src/focusguard/
```

See [Architecture](docs/ARCHITECTURE.md) for the module map and where new features should go.

---

## License

MIT — do whatever you want with it.