"""
N E X U S  —  Multi-LLM Provider Engine
Supports Claude, OpenAI, Google, xAI, DeepSeek, Mistral, Meta
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass

import aiohttp

from nexus_app.config import load_config, save_config, get_api_key


@dataclass
class Model:
    id: str
    name: str
    provider: str
    api_model: str  # actual model ID sent to the API


# ── All supported models ──
MODELS = [
    # Anthropic (via Claude CLI)
    Model("claude-opus", "Claude Opus 4.6", "claude", "claude-opus-4-6"),
    Model("claude-sonnet", "Claude Sonnet 4.6", "claude", "claude-sonnet-4-6"),
    Model("claude-haiku", "Claude Haiku 4.5", "claude", "claude-haiku-4-5"),

    # OpenAI
    Model("gpt-4o", "GPT-4o", "openai", "gpt-4o"),
    Model("gpt-4o-mini", "GPT-4o Mini", "openai", "gpt-4o-mini"),
    Model("o3", "OpenAI o3", "openai", "o3"),
    Model("o3-mini", "OpenAI o3-mini", "openai", "o3-mini"),
    Model("o4-mini", "OpenAI o4-mini", "openai", "o4-mini"),

    # Google
    Model("gemini-2.5-pro", "Gemini 2.5 Pro", "google", "gemini-2.5-pro-preview-06-05"),
    Model("gemini-2.5-flash", "Gemini 2.5 Flash", "google", "gemini-2.5-flash-preview-05-20"),
    Model("gemini-2.0-flash", "Gemini 2.0 Flash", "google", "gemini-2.0-flash"),

    # xAI (Grok)
    Model("grok-3", "Grok 3", "xai", "grok-3"),
    Model("grok-3-mini", "Grok 3 Mini", "xai", "grok-3-mini"),
    Model("grok-3-fast", "Grok 3 Fast", "xai", "grok-3-fast"),

    # DeepSeek
    Model("deepseek-v3", "DeepSeek V3", "deepseek", "deepseek-chat"),
    Model("deepseek-r1", "DeepSeek R1", "deepseek", "deepseek-reasoner"),

    # Mistral
    Model("mistral-large", "Mistral Large", "mistral", "mistral-large-latest"),
    Model("codestral", "Codestral", "mistral", "codestral-latest"),

    # Meta (via Together AI)
    Model("llama-4-maverick", "Llama 4 Maverick", "together", "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"),
    Model("llama-3.3-70b", "Llama 3.3 70B", "together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),

    # Groq (fast inference)
    Model("groq-llama-3.3", "Llama 3.3 70B (Groq)", "groq", "llama-3.3-70b-versatile"),
    Model("groq-mixtral", "Mixtral 8x7B (Groq)", "groq", "mixtral-8x7b-32768"),
]

# Provider -> API base URL
PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "google": "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse",
    "xai": "https://api.x.ai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "together": "https://api.together.xyz/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
}

# Provider -> env var name for API key
PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "together": "TOGETHER_API_KEY",
    "groq": "GROQ_API_KEY",
}



def get_model(model_id: str) -> Model | None:
    for m in MODELS:
        if m.id == model_id:
            return m
    return None


def get_models_dict() -> list[dict]:
    """Return models as JSON-serializable list."""
    return [
        {"id": m.id, "name": m.name, "provider": m.provider}
        for m in MODELS
    ]


async def stream_openai_compatible(
    url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    on_chunk,
):
    """Stream from any OpenAI-compatible API (OpenAI, xAI, DeepSeek, Mistral, Together, Groq)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"API error {resp.status}: {error_text[:300]}")

            async for line in resp.content:
                decoded = line.decode("utf-8", errors="replace").strip()
                if not decoded or not decoded.startswith("data: "):
                    continue

                data_str = decoded[6:]
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        await on_chunk(content)
                except json.JSONDecodeError:
                    continue


async def stream_google(
    api_key: str,
    model: str,
    messages: list[dict],
    on_chunk,
):
    """Stream from Google Gemini API."""
    url = PROVIDER_URLS["google"].format(model=model)
    url += f"&key={api_key}"

    # Convert messages to Gemini format
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}],
        })

    payload = {"contents": contents}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Gemini API error {resp.status}: {error_text[:300]}")

            async for line in resp.content:
                decoded = line.decode("utf-8", errors="replace").strip()
                if not decoded or not decoded.startswith("data: "):
                    continue

                try:
                    data = json.loads(decoded[6:])
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            text = part.get("text", "")
                            if text:
                                await on_chunk(text)
                except json.JSONDecodeError:
                    continue


async def stream_api_response(
    model: Model,
    messages: list[dict],
    on_chunk,
):
    """Route to the correct provider and stream response."""
    provider = model.provider
    api_key = get_api_key(provider)

    if not api_key:
        raise Exception(
            f"No API key for {provider}. Set it in NEXUS settings or "
            f"export {PROVIDER_KEY_ENV.get(provider, 'KEY')} env var."
        )

    if provider == "google":
        await stream_google(api_key, model.api_model, messages, on_chunk)
    else:
        url = PROVIDER_URLS[provider]
        await stream_openai_compatible(url, api_key, model.api_model, messages, on_chunk)
