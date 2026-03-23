# N E X U S

**Personal AI Command Center** — by Muhammad Rashid

A Tony Stark-inspired terminal that connects to every major LLM and all your dev tools in one native interface.

## Install

```bash
pip install nexus-terminal
```

Or clone:
```bash
git clone https://github.com/muhammadrashid4587/nexus-terminal.git
cd nexus-terminal
pip install -e .
```

## Usage

Three modes:

```bash
nexus                      # Native window (default)
nexus --inline             # Run in current terminal
nexus --browser            # Open in browser
```

Options:
```bash
nexus /path/to/project     # Open in specific directory
nexus --port 8888          # Custom port
nexus -i                   # Short for --inline
```

## Models

Switch between 22 models across 8 providers on the fly:

| Provider | Models |
|----------|--------|
| Anthropic | Claude Opus 4.6, Sonnet 4.6, Haiku 4.5 |
| OpenAI | GPT-4o, GPT-4o Mini, o3, o3-mini, o4-mini |
| Google | Gemini 2.5 Pro, 2.5 Flash, 2.0 Flash |
| xAI | Grok 3, Grok 3 Mini, Grok 3 Fast |
| DeepSeek | V3, R1 |
| Mistral | Large, Codestral |
| Meta | Llama 4 Maverick, Llama 3.3 70B |
| Groq | Llama 3.3 70B, Mixtral 8x7B |

Claude models use your existing CLI auth. Other providers need an API key (set via UI or env vars).

## Integrations

Built-in plugins with slash commands:

**GitHub** — `/gh`, `/gh repos`, `/gh prs`, `/gh notifications`, `/gh activity`

**System** — `/sys`, `/sys cpu`, `/sys mem`, `/sys procs`, `/sys net`, `/sys disk`

**Git** — `/git`, `/git log`, `/git branches`, `/git diff`, `/git stash`

## Config

All config stored in `~/.nexus/`. API keys can be set via the gear icon in the UI or environment variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `XAI_API_KEY`, etc).

## License

MIT
