"""NEXUS web server — serves UI, handles WebSocket, manages plugins."""

import asyncio
import json
import os
import shutil
import weakref
from pathlib import Path

import aiohttp
from aiohttp import web

from nexus_app.config import load_config, save_config, get_api_key
from nexus_app.providers import (
    get_model, get_models_dict, stream_api_response,
)
from nexus_app.plugins.base import PluginManager
from nexus_app.plugins.github import GitHubPlugin
from nexus_app.plugins.system import SystemPlugin
from nexus_app.plugins.git_local import GitLocalPlugin

STATIC_DIR = Path(__file__).parent / "static"
CLAUDE_BIN = shutil.which("claude") or "claude"


class NexusSession:
    """Manages a conversation with any LLM + plugin commands."""

    def __init__(self, ws: web.WebSocketResponse, cwd: str, plugins: PluginManager):
        self.ws = ws
        self.cwd = cwd
        self.plugins = plugins
        self.process = None
        self.conversation_id = None
        self.selected_model = load_config().get("selected_model", "claude-opus")
        self.chat_history = []
        self._abort_flag = False

    async def send_json(self, data: dict):
        try:
            await self.ws.send_json(data)
        except (ConnectionResetError, ConnectionError):
            pass

    async def run_prompt(self, prompt: str):
        """Route: plugin command → Claude CLI → API provider."""

        # Check for plugin commands (slash commands)
        if prompt.startswith("/"):
            parts = prompt.split(maxsplit=1)
            cmd = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            # Try plugins first
            result = await self.plugins.handle_command(cmd, args)
            if result is not None:
                await self.send_json({"type": "stream_start"})
                await self.send_json({"type": "stream_chunk", "content": result})
                await self.send_json({"type": "stream_end"})
                return

        # Route to model
        model = get_model(self.selected_model) or get_model("claude-opus")

        if model.provider == "claude":
            await self._run_claude_cli(prompt, model.api_model)
        else:
            await self._run_api(prompt, model)

    async def _run_claude_cli(self, prompt: str, model_id: str):
        await self.send_json({"type": "stream_start"})
        cmd = [CLAUDE_BIN, "--verbose", "--output-format", "stream-json",
               "--model", model_id]
        if self.conversation_id:
            cmd.extend(["--resume", self.conversation_id])
        cmd.extend(["-p", prompt])

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, cwd=self.cwd,
            )
            full_text = ""
            async for line in self.process.stdout:
                decoded = line.decode("utf-8", errors="replace").strip()
                if not decoded:
                    continue
                try:
                    msg = json.loads(decoded)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type", "")
                if msg_type == "system" and msg.get("session_id"):
                    self.conversation_id = msg["session_id"]
                elif msg_type == "assistant":
                    content = msg.get("message", {})
                    if isinstance(content, dict):
                        for block in content.get("content", []):
                            if block.get("type") == "text":
                                text = block.get("text", "")
                                delta = text[len(full_text):]
                                if delta:
                                    full_text = text
                                    await self.send_json({"type": "stream_chunk", "content": delta})
                            elif block.get("type") == "tool_use":
                                await self.send_json({
                                    "type": "tool_use",
                                    "tool": block.get("name", "unknown"),
                                    "content": json.dumps(block.get("input", {}))[:200],
                                })
                elif msg_type == "content_block_delta":
                    delta = msg.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            await self.send_json({"type": "stream_chunk", "content": text})
                elif msg_type == "result":
                    sid = msg.get("session_id")
                    if sid:
                        self.conversation_id = sid
                    result_text = msg.get("result", "")
                    if result_text and not full_text:
                        await self.send_json({"type": "stream_chunk", "content": result_text})

            await self.process.wait()
            if self.process.returncode and self.process.returncode != 0:
                stderr = await self.process.stderr.read()
                err = stderr.decode().strip()
                if err and not full_text:
                    await self.send_json({"type": "error", "content": err[:500]})
        except asyncio.CancelledError:
            if self.process:
                self.process.terminate()
            raise
        except Exception as e:
            await self.send_json({"type": "error", "content": str(e)})
        finally:
            self.process = None
            await self.send_json({"type": "stream_end"})

    async def _run_api(self, prompt, model):
        await self.send_json({"type": "stream_start"})
        self._abort_flag = False
        self.chat_history.append({"role": "user", "content": prompt})
        messages = [
            {"role": "system", "content": f"You are NEXUS, an advanced AI assistant. Working dir: {self.cwd}"},
            *self.chat_history,
        ]
        full_response = ""
        try:
            async def on_chunk(text):
                nonlocal full_response
                if self._abort_flag:
                    raise asyncio.CancelledError()
                full_response += text
                await self.send_json({"type": "stream_chunk", "content": text})
            await stream_api_response(model, messages, on_chunk)
            if full_response:
                self.chat_history.append({"role": "assistant", "content": full_response})
            if len(self.chat_history) > 40:
                self.chat_history = self.chat_history[-30:]
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.send_json({"type": "error", "content": str(e)})
        finally:
            await self.send_json({"type": "stream_end"})

    async def abort(self):
        self._abort_flag = True
        if self.process:
            try:
                self.process.terminate()
                await asyncio.sleep(0.5)
                if self.process and self.process.returncode is None:
                    self.process.kill()
            except ProcessLookupError:
                pass

    async def reset(self):
        await self.abort()
        self.conversation_id = None
        self.chat_history = []


def create_app(working_dir: str) -> web.Application:
    """Create and configure the NEXUS web application."""
    app = web.Application()
    app["working_dir"] = working_dir
    app["sessions"] = weakref.WeakSet()

    # Initialize plugins
    plugins = PluginManager()
    plugins.register(GitHubPlugin())
    plugins.register(SystemPlugin())
    plugins.register(GitLocalPlugin(working_dir))
    app["plugins"] = plugins

    # Routes
    app.router.add_get("/", handle_index)
    app.router.add_get("/ws", handle_websocket)
    app.router.add_get("/api/info", handle_info)
    app.router.add_get("/api/plugins", handle_plugins)
    app.router.add_post("/api/model", handle_set_model)
    app.router.add_post("/api/key", handle_set_key)
    app.router.add_get("/static/{filename:.*}", handle_static)

    return app


async def handle_index(request):
    return web.FileResponse(STATIC_DIR / "index.html")


async def handle_static(request):
    filename = request.match_info["filename"]
    filepath = STATIC_DIR / filename
    if filepath.exists() and filepath.is_file():
        return web.FileResponse(filepath)
    return web.Response(status=404)


async def handle_info(request):
    config = load_config()
    return web.json_response({
        "cwd": request.app["working_dir"],
        "version": "2.0.0",
        "models": get_models_dict(),
        "selected_model": config.get("selected_model", "claude-opus"),
        "configured_keys": [
            p for p in ["openai", "google", "xai", "deepseek", "mistral", "together", "groq"]
            if get_api_key(p)
        ],
        "owner": config.get("owner", {}),
    })


async def handle_plugins(request):
    plugins = request.app["plugins"]
    statuses = await plugins.get_all_status()
    data = await plugins.get_all_data()
    return web.json_response({"statuses": statuses, "data": data})


async def handle_set_model(request):
    data = await request.json()
    model_id = data.get("model")
    if not get_model(model_id):
        return web.json_response({"error": "Unknown model"}, status=400)
    config = load_config()
    config["selected_model"] = model_id
    save_config(config)
    return web.json_response({"ok": True})


async def handle_set_key(request):
    data = await request.json()
    provider = data.get("provider", "")
    key = data.get("key", "").strip()
    if not provider or not key:
        return web.json_response({"error": "Missing data"}, status=400)
    config = load_config()
    if "api_keys" not in config:
        config["api_keys"] = {}
    config["api_keys"][provider] = key
    save_config(config)
    return web.json_response({"ok": True})


async def handle_websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    plugins = request.app["plugins"]
    session = NexusSession(ws, request.app["working_dir"], plugins)
    request.app["sessions"].add(session)

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                cmd = data.get("type", "")
                if cmd == "prompt":
                    content = data.get("content", "").strip()
                    if content:
                        await session.run_prompt(content)
                elif cmd == "abort":
                    await session.abort()
                elif cmd == "clear":
                    await session.reset()
                elif cmd == "set_model":
                    model_id = data.get("model", "")
                    if get_model(model_id):
                        session.selected_model = model_id
                        config = load_config()
                        config["selected_model"] = model_id
                        save_config(config)
                        session.conversation_id = None
                        session.chat_history = []
                        await session.send_json({"type": "model_changed", "model": model_id})
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
    finally:
        await session.abort()
    return ws
