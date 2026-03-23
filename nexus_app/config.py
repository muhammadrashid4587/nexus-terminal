"""NEXUS configuration management. Stores keys, prefs, connections."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".nexus"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONNECTIONS_FILE = CONFIG_DIR / "connections.json"

DEFAULT_CONFIG = {
    "version": "2.0.0",
    "selected_model": "claude-opus",
    "api_keys": {},
    "theme": "red-gold",
    "owner": {
        "name": "Muhammad Rashid",
        "handle": "muhammadrashid4587",
    },
    "integrations": {
        "github": True,
        "system": True,
        "git": True,
    },
}


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key(provider: str) -> str | None:
    """Get API key from config or environment."""
    config = load_config()
    key = config.get("api_keys", {}).get(provider)
    if key:
        return key
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "xai": "XAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "together": "TOGETHER_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    env_var = env_map.get(provider)
    return os.environ.get(env_var) if env_var else None


def load_connections() -> dict:
    """Load connected service states."""
    ensure_config_dir()
    if CONNECTIONS_FILE.exists():
        try:
            return json.loads(CONNECTIONS_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_connections(data: dict):
    ensure_config_dir()
    CONNECTIONS_FILE.write_text(json.dumps(data, indent=2))
