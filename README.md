# N E X U S

**Personal AI Command Center** — by Muhammad Rashid

A Tony Stark-inspired terminal that connects to every major LLM and all your dev tools in one native interface.

## Install

**One command:**
```bash
curl -fsSL https://raw.githubusercontent.com/muhammadrashid4587/nexus-terminal/main/install.sh | bash
```

**Or with pipx (recommended on macOS):**
```bash
brew install pipx
pipx install git+https://github.com/muhammadrashid4587/nexus-terminal.git
```

**Or with pip (in a venv):**
```bash
pip install nexus-terminal
```

**Or from source:**
```bash
git clone https://github.com/muhammadrashid4587/nexus-terminal.git
cd nexus-terminal
pip install -e .
```

## Quick Start

```bash
nexus                      # Native window (default)
nexus --inline             # Run in current terminal
nexus --browser            # Open in browser
nexus -i                   # Short for --inline
nexus /path/to/project     # Open in specific directory
nexus --port 8888          # Custom port
```

## Features

### 22 Models, 8 Providers

Switch between any LLM on the fly from the dropdown or with `/model <id>`:

| Provider | Models |
|----------|--------|
| **Anthropic** | Claude Opus 4.6, Sonnet 4.6, Haiku 4.5 |
| **OpenAI** | GPT-4o, GPT-4o Mini, o3, o3-mini, o4-mini |
| **Google** | Gemini 2.5 Pro, 2.5 Flash, 2.0 Flash |
| **xAI** | Grok 3, Grok 3 Mini, Grok 3 Fast |
| **DeepSeek** | V3, R1 |
| **Mistral** | Large, Codestral |
| **Meta** | Llama 4 Maverick, Llama 3.3 70B |
| **Groq** | Llama 3.3 70B, Mixtral 8x7B |

Claude models use your existing `claude` CLI auth. Other providers need an API key.

### Built-in Integrations

Slash commands that connect to your real data:

**GitHub**
```
/gh                  GitHub profile overview
/gh repos            Your repositories
/gh prs              Open pull requests
/gh issues           Open issues
/gh notifications    Notifications
/gh activity         Recent activity feed
```

**System Monitoring**
```
/sys                 System overview (OS, CPU, RAM, disk)
/sys cpu             CPU usage per core with bars
/sys mem             Memory + swap usage
/sys procs           Top 15 processes by CPU
/sys net             Network stats + IP addresses
/sys disk            Disk usage per partition
```

**Git**
```
/git                 Current repo status
/git log             Last 20 commits (graph)
/git branches        All branches sorted by date
/git diff            Current changes
/git stash           List stashes
```

### Three Launch Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Window** | `nexus` | Native desktop window with full UI, 3D globe, panels |
| **Inline** | `nexus -i` | Runs in your current terminal, no window needed |
| **Browser** | `nexus --browser` | Opens in your default browser |

### Tony Stark UI

- 3D rotating wireframe globe with arc reactor rings
- Red & gold holographic theme
- HUD-style panels with live system stats
- Animated boot sequence
- Scanline overlay

## API Keys

Claude works out of the box via `claude` CLI. For other providers:

**Option 1: UI** — Click the gear icon next to MODEL in the right panel

**Option 2: Environment variables**
```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AIza..."
export XAI_API_KEY="xai-..."
export DEEPSEEK_API_KEY="sk-..."
export MISTRAL_API_KEY="..."
export TOGETHER_API_KEY="..."
export GROQ_API_KEY="gsk_..."
```

## Config

All configuration stored in `~/.nexus/config.json`. Persists across sessions and machines.

## Requirements

- Python 3.10+
- `claude` CLI (for Anthropic models)
- `gh` CLI (for GitHub integration, optional)

## Development

```bash
git clone https://github.com/muhammadrashid4587/nexus-terminal.git
cd nexus-terminal
pip install -e .
nexus --browser    # develop with hot reload in browser
```

## Publishing to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
# Username: __token__
# Password: your PyPI API token (pypi-...)
```

## License

MIT
