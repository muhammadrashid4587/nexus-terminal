#!/usr/bin/env python3
"""
N E X U S  —  Neural Execution & Unified System
Multi-LLM Tony Stark terminal. Supports Claude, OpenAI, Gemini, Grok, DeepSeek, Mistral, Llama.
"""

import asyncio
import json
import os
import shutil
import sys
import threading
import weakref
from pathlib import Path

import aiohttp
from aiohttp import web

from providers import (
    MODELS, get_model, get_models_dict, get_api_key,
    load_config, save_config, stream_api_response,
)

# ── Configuration ──
HOST = "127.0.0.1"
PORT = int(os.environ.get("NEXUS_PORT", 7777))
CLAUDE_BIN = shutil.which("claude") or "claude"
STATIC_DIR = Path(__file__).parent / "static"
WORKING_DIR = os.environ.get("NEXUS_CWD", os.getcwd())


class NexusSession:
    """Manages a conversation with any LLM."""

    def __init__(self, ws: web.WebSocketResponse, cwd: str):
        self.ws = ws
        self.cwd = cwd
        self.process: asyncio.subprocess.Process | None = None
        self.conversation_id: str | None = None
        self.selected_model: str = load_config().get("selected_model", "claude-opus")
        self.chat_history: list[dict] = []  # For API-based models
        self._abort_flag = False

    async def send_json(self, data: dict):
        try:
            await self.ws.send_json(data)
        except (ConnectionResetError, ConnectionError):
            pass

    async def run_prompt(self, prompt: str):
        """Route to Claude CLI or API based on selected model."""
        model = get_model(self.selected_model)
        if not model:
            model = get_model("claude-opus")

        if model.provider == "claude":
            await self._run_claude_cli(prompt, model.api_model)
        else:
            await self._run_api(prompt, model)

    async def _run_claude_cli(self, prompt: str, model_id: str):
        """Send prompt via Claude CLI."""
        await self.send_json({"type": "stream_start"})

        cmd = [CLAUDE_BIN, "--verbose", "--output-format", "stream-json",
               "--model", model_id]

        if self.conversation_id:
            cmd.extend(["--resume", self.conversation_id])

        cmd.extend(["-p", prompt])

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
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
                    usage = msg.get("usage", {})
                    token_info = ""
                    if usage:
                        token_info = f"{usage.get('input_tokens', 0) + usage.get('output_tokens', 0):,}"
                    total_cost = msg.get("total_cost_usd")
                    await self.send_json({
                        "type": "status",
                        "tokens": token_info or "--",
                        "cost": f"${total_cost:.4f}" if total_cost else None,
                    })
                    result_text = msg.get("result", "")
                    if result_text and not full_text:
                        await self.send_json({"type": "stream_chunk", "content": result_text})

            await self.process.wait()

            if self.process.returncode and self.process.returncode != 0:
                stderr = await self.process.stderr.read()
                err_text = stderr.decode("utf-8", errors="replace").strip()
                if err_text and not full_text:
                    await self.send_json({"type": "error", "content": err_text[:500]})

        except asyncio.CancelledError:
            if self.process:
                self.process.terminate()
            raise
        except Exception as e:
            await self.send_json({"type": "error", "content": str(e)})
        finally:
            self.process = None
            await self.send_json({"type": "stream_end"})

    async def _run_api(self, prompt: str, model):
        """Send prompt via direct API call (OpenAI, Gemini, Grok, etc.)."""
        await self.send_json({"type": "stream_start"})
        self._abort_flag = False

        # Add user message to history
        self.chat_history.append({"role": "user", "content": prompt})

        # System prompt
        messages = [
            {"role": "system", "content": (
                "You are NEXUS, an advanced AI assistant. You are helpful, direct, and concise. "
                "You write clean code and give clear explanations. "
                f"The user's working directory is: {self.cwd}"
            )},
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

            # Save assistant response to history
            if full_response:
                self.chat_history.append({"role": "assistant", "content": full_response})

            # Keep history manageable
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


# ── Web Application ──
app = web.Application()
active_sessions: weakref.WeakSet = weakref.WeakSet()


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
        "cwd": WORKING_DIR,
        "claude_bin": CLAUDE_BIN,
        "version": "2.0.0",
        "models": get_models_dict(),
        "selected_model": config.get("selected_model", "claude-opus"),
        "configured_keys": [
            p for p in ["openai", "google", "xai", "deepseek", "mistral", "together", "groq"]
            if get_api_key(p)
        ],
    })


async def handle_set_model(request):
    data = await request.json()
    model_id = data.get("model")
    if not get_model(model_id):
        return web.json_response({"error": "Unknown model"}, status=400)
    config = load_config()
    config["selected_model"] = model_id
    save_config(config)
    return web.json_response({"ok": True, "model": model_id})


async def handle_set_key(request):
    data = await request.json()
    provider = data.get("provider", "")
    key = data.get("key", "").strip()
    if not provider or not key:
        return web.json_response({"error": "Missing provider or key"}, status=400)
    config = load_config()
    if "api_keys" not in config:
        config["api_keys"] = {}
    config["api_keys"][provider] = key
    save_config(config)
    return web.json_response({"ok": True})


async def handle_websocket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    session = NexusSession(ws, WORKING_DIR)
    active_sessions.add(session)

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
                        # Reset conversation when switching models
                        session.conversation_id = None
                        session.chat_history = []
                        await session.send_json({
                            "type": "model_changed",
                            "model": model_id,
                        })

            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
    finally:
        await session.abort()

    return ws


# ── Routes ──
app.router.add_get("/", handle_index)
app.router.add_get("/ws", handle_websocket)
app.router.add_get("/api/info", handle_info)
app.router.add_post("/api/model", handle_set_model)
app.router.add_post("/api/key", handle_set_key)
app.router.add_get("/static/{filename:.*}", handle_static)


# ── Banner ──
BANNER = r"""
[38;2;255;26;26m
  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
[0m
  [2mNeural Execution & Unified System  v2.0[0m
  [2mMulti-LLM Engine[0m
"""


def start_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, HOST, PORT)
    loop.run_until_complete(site.start())
    loop.run_forever()


def main():
    print(BANNER)
    print(f"  \033[38;2;255;26;26m▸\033[0m Claude:   {CLAUDE_BIN}")
    print(f"  \033[38;2;255;26;26m▸\033[0m Workdir:  {WORKING_DIR}")
    print(f"  \033[38;2;255;26;26m▸\033[0m Port:     {PORT}")
    print()

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    import time
    time.sleep(0.5)

    if "--browser" in sys.argv:
        import webbrowser
        print(f"  \033[38;2;255;26;26m▸\033[0m Opening in browser...")
        webbrowser.open(f"http://{HOST}:{PORT}")
        print(f"  \033[38;2;255;26;26m▸\033[0m Running at http://{HOST}:{PORT}")
        print(f"  \033[38;2;255;26;26m▸\033[0m Press Ctrl+C to shutdown")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  Shutting down...")
            sys.exit(0)
    else:
        try:
            import webview
            print(f"  \033[38;2;255;215;0m▸\033[0m Launching native window...")
            print()
            window = webview.create_window(
                title="N E X U S",
                url=f"http://{HOST}:{PORT}",
                width=1400,
                height=900,
                min_size=(900, 600),
                background_color="#0a0508",
                text_select=True,
            )
            webview.start(debug=False)
            print("\n  Window closed. Shutting down...")
            sys.exit(0)
        except ImportError:
            import webbrowser
            webbrowser.open(f"http://{HOST}:{PORT}")
            print(f"  \033[38;2;255;26;26m▸\033[0m Running at http://{HOST}:{PORT}")
            print(f"  \033[38;2;255;26;26m▸\033[0m Press Ctrl+C to shutdown")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n  Shutting down...")
                sys.exit(0)


if __name__ == "__main__":
    main()
