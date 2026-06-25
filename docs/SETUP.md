# FocusGuard — Setup Guide

## Part 1: Installation

### Step 1 — Navigate to the project
```bash
cd path/to/focusguard
```

### Step 2 — Create virtual environment & install
```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Alternative: install globally (no virtual environment)
If you want the `focusguard` command available from any folder without activating a venv, use `pipx`:
```bash
# 1. Install pipx if you don't have it
# macOS:   brew install pipx
# Linux:   python3 -m pip install --user pipx
# Windows: py -m pip install --user pipx
pipx ensurepath

# 2. Install FocusGuard
pipx install .

# 3. Restart your terminal
```

### Step 3 — Verify it works
```bash
focusguard --version
# → FocusGuard v0.1.0

focusguard --help
# → Shows all commands
```

> [!NOTE]
> **macOS users**: You may need to grant Accessibility permissions for window title tracking.
> Go to **System Settings → Privacy & Security → Accessibility** → add your terminal app (Terminal, iTerm, Warp, etc.)
>
> **Linux (Wayland) users**: Window title access is restricted by design on Wayland. FocusGuard works best on X11. On Wayland, only app names are tracked, not window titles.
>
> **Windows users**: `psutil` may trigger antivirus warnings — this is a false positive. FocusGuard never injects into processes, captures keystrokes, or records the screen. See the README's Antivirus FAQ.

---

## Part 2: Basic Usage

### Start tracking
```bash
# Foreground mode (see output, Ctrl+C to stop)
focusguard start

# Background mode (detaches from terminal)
focusguard start -d
```

### Check your stats
```bash
# Quick one-liner
focusguard stats
# → Focus: 78/100  |  Coding: 3h 42m  |  Distraction: 27m

# Full dashboard
focusguard report

# Weekly summary
focusguard report -p week
```

### Stop tracking
```bash
focusguard stop
```

---

## Part 3: Goals

### Set a goal
```bash
focusguard goal add "Build authentication system"
# → Goal #1 created
```

### List your goals
```bash
focusguard goal list
```

### Complete or drop
```bash
focusguard goal complete 1    # Mark as done
focusguard goal drop 2        # Abandon without completing
```

---

## Part 4: Daemon (survive terminal close)

This is the most important setup step. Without it, tracking stops the moment you close the terminal.

### Install the daemon
```bash
focusguard daemon install
# → FocusGuard daemon installed successfully
# → It will start automatically on login.
```

This creates a platform-specific background service:

| OS | What gets created |
|---|---|
| macOS | `~/Library/LaunchAgents/com.focusguard.tracker.plist` (launchd) |
| Linux | `~/.config/systemd/user/focusguard.service` (systemd user service) |
| Windows | A Task Scheduler entry running at user logon |

> [!NOTE]
> Windows daemon support is newer and less battle-tested than macOS/Linux. If `daemon install` doesn't behave as expected on Windows, please open an issue with your Windows version.

### Check daemon status
```bash
focusguard daemon status
# → FocusGuard is running (PID: 12345)
```

### Remove the daemon
```bash
focusguard daemon uninstall
```

---

## Part 5: AI Coach Setup

The AI coach is fully **opt-in** — nothing is sent anywhere until you explicitly enable it and run a coach command. Two backends are supported:

- **Ollama** (local, free, private — recommended) — your goal and stuck-time context never leave your machine
- **OpenAI** (paid, cloud) — minimal context is sent per request

### Option A — Ollama (local)

**Step 1 — Make sure Ollama is running**
```bash
ollama serve
```

**Step 2 — Pull a model**

`llama3.2:3b` is a good default — capable enough for useful hints, light enough to run on most laptops (6GB+ RAM):
```bash
ollama pull llama3.2:3b
ollama list   # confirm it shows up
```

> [!TIP]
> On a low-RAM machine, smaller models like `qwen2.5:0.5b` or `qwen3:0.6b` will run faster but give noticeably weaker hints. Start with `llama3.2:3b` if your machine can handle it.

**Step 3 — Create the config file**
```bash
mkdir -p ~/.config/focusguard
cat > ~/.config/focusguard/config.toml << 'EOF'
[ai]
enabled = true
provider = "ollama"
ollama_model = "llama3.2:3b"

[personality]
mode = "coach"
EOF
```

### Option B — OpenAI (cloud)
```bash
focusguard coach setup-openai
# → Prompts for your API key (hidden input)
# → Stored securely in OS keyring — never in a file
```
Then set `provider = "openai"` in your config.

### Try it
```bash
# Set a goal first (the AI uses this as context)
focusguard goal add "Fix the login bug"

# Ask for help
focusguard coach help

# Break your goal into subtasks
focusguard coach help -b

# Get roasted
focusguard roast
```

---

## Part 6: Personality Modes

```bash
focusguard coach mode coach     # Encouraging
focusguard coach mode strict    # No-nonsense
focusguard coach mode friend    # Casual
focusguard coach mode roast     # Savage

# Quick shortcut
focusguard roast

# Get a nudge in your current mode
focusguard coach nudge

# Disable AI (fall back to local text templates)
focusguard coach disable
```

> [!TIP]
> Personality modes work **with or without AI enabled**. Without AI, you get template-based messages built from your real stats. With AI, responses are more dynamic and specific to your situation.

---

## Part 7: GitHub Integration (optional)

### Step 1 — Create a GitHub personal access token
Go to **github.com/settings/tokens** → Generate new token → select the `repo` scope (read-only is sufficient).

### Step 2 — Configure
```bash
focusguard github setup
# → Prompts for your token (hidden input)
# → Stored securely in OS keyring — never in a file
```

### Step 3 — Use it
```bash
focusguard github summary
focusguard github repos ~/Code     # path to wherever your local repos live
```

---

## Part 8: Privacy Controls

```bash
# See exactly what is and isn't tracked
focusguard privacy show

# View or extend the sensitive-site blocklist
focusguard privacy blocklist
focusguard privacy blocklist add "mycompany-internal"

# Back up your database encryption key
focusguard privacy export-key
# → Prints the key — save it in a password manager, not a text file
```

---

## Part 9: Configuration Reference

Config file location:

| OS | Path |
|---|---|
| macOS / Linux | `~/.config/focusguard/config.toml` |
| Windows | `%APPDATA%\focusguard\config.toml` |

Everything below is optional — sensible defaults are built in.

```toml
[tracker]
poll_interval = 60          # seconds between checks
idle_threshold = 300        # seconds before marking idle

[security]
blocklist = ["chase", "healthcare", "private", "mybank.com"]
retention_days = 90         # auto-delete raw logs older than this

[personality]
mode = "coach"               # coach, strict, friend, roast

[ai]
enabled = false
provider = "ollama"          # ollama or openai
ollama_model = "llama3.2:3b"
# openai_model = "gpt-4o-mini"   # if using OpenAI instead
```

---

## Part 10: Complete Uninstall

### Option A — full cleanup (removes everything)
```bash
focusguard privacy uninstall --yes
```

This removes the background daemon, the encrypted database, config files, logs, and every keyring entry (encryption key, GitHub token, API keys) — on whichever OS you're running.

### Option B — manual step-by-step removal

```bash
# 1. Stop the tracker
focusguard stop

# 2. Remove the daemon
focusguard daemon uninstall

# 3. Uninstall the package
pip uninstall focusguard
# or, if installed globally:
pipx uninstall focusguard

# 4. Remove data directories
# macOS:
rm -rf ~/.config/focusguard
rm -rf ~/Library/Application\ Support/focusguard
rm -rf ~/Library/Logs/focusguard

# Linux:
rm -rf ~/.config/focusguard
rm -rf ~/.local/share/focusguard

# Windows (PowerShell):
# Remove-Item -Recurse -Force "$env:APPDATA\focusguard"
# Remove-Item -Recurse -Force "$env:LOCALAPPDATA\focusguard"

# 5. Remove the virtual environment (if you used one)
cd path/to/focusguard
rm -rf .venv

# 6. (Optional) Delete the source code
cd ..
rm -rf focusguard
```

### Option C — keep data, just stop tracking
```bash
focusguard stop
focusguard daemon uninstall
# Your data stays in place.
# Reinstall later and FocusGuard picks up where you left off.
```

---

## Quick Reference Card

| What you want | Command |
|---|---|
| Start tracking | `focusguard start -d` |
| Stop tracking | `focusguard stop` |
| Quick stats | `focusguard stats` |
| Full dashboard | `focusguard report` |
| Set a goal | `focusguard goal add "..."` |
| Get roasted | `focusguard roast` |
| AI help | `focusguard coach help` |
| Disable AI | `focusguard coach disable` |
| Install daemon | `focusguard daemon install` |
| What's tracked | `focusguard privacy show` |
| Remove everything | `focusguard privacy uninstall --yes` |
