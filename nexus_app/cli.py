#!/usr/bin/env python3
"""
N E X U S  —  CLI Entry Point
Usage:
    nexus                     Launch native window (default)
    nexus --inline            Run in current terminal (TUI mode)
    nexus --browser           Open in browser
    nexus /path/to/project    Launch in specific directory
    nexus --port 8888         Custom port
    nexus --version           Show version
"""

import argparse
import asyncio
import json
import os
import sys
import threading
import time

from aiohttp import web

from nexus_app import __version__
from nexus_app.server import create_app

HOST = "127.0.0.1"

BANNER = r"""
[38;2;255;26;26m
  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
[0m
  [2mNeural Execution & Unified System  v{version}[0m
  [2mPersonal AI Command Center[0m
"""

R = "\033[38;2;255;26;26m"
G = "\033[38;2;255;215;0m"
D = "\033[2m"
B = "\033[1m"
X = "\033[0m"


def start_server(app, host, port):
    """Run server in background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, host, port)
    loop.run_until_complete(site.start())
    loop.run_forever()


def run_inline(cwd: str, port: int):
    """Run NEXUS directly in the current terminal — no window, no browser."""
    import shutil
    from nexus_app.config import load_config
    from nexus_app.providers import get_model
    from nexus_app.plugins.base import PluginManager
    from nexus_app.plugins.github import GitHubPlugin
    from nexus_app.plugins.system import SystemPlugin
    from nexus_app.plugins.git_local import GitLocalPlugin

    CLAUDE_BIN = shutil.which("claude") or "claude"

    # Init plugins
    plugins = PluginManager()
    plugins.register(GitHubPlugin())
    plugins.register(SystemPlugin())
    plugins.register(GitLocalPlugin(cwd))

    config = load_config()
    selected_model = config.get("selected_model", "claude-opus")
    conversation_id = None
    chat_history = []

    print(BANNER.format(version=__version__))
    print(f"  {R}▸{X} Mode:     {G}INLINE TERMINAL{X}")
    print(f"  {R}▸{X} Workdir:  {cwd}")
    print(f"  {R}▸{X} Model:    {selected_model}")
    print(f"  {R}▸{X} Type {G}/help{X} for commands, {G}exit{X} to quit")
    print()

    async def handle_plugin_command(text):
        """Try to handle as a plugin slash command. Returns True if handled."""
        if not text.startswith("/"):
            return False

        parts = text.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        result = await plugins.handle_command(cmd, args)
        if result is not None:
            # Simple markdown-like output for terminal
            output = result.replace("**", f"{B}").replace("**", f"{X}")
            print(f"\n{output}\n")
            return True
        return False

    async def run_claude_prompt(prompt):
        """Run a prompt through Claude CLI and stream output."""
        nonlocal conversation_id

        model = get_model(selected_model)
        model_id = model.api_model if model else "claude-opus-4-6"

        cmd = [CLAUDE_BIN, "--verbose", "--output-format", "stream-json",
               "--model", model_id]
        if conversation_id:
            cmd.extend(["--resume", conversation_id])
        cmd.extend(["-p", prompt])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        full_text = ""
        async for line in proc.stdout:
            decoded = line.decode("utf-8", errors="replace").strip()
            if not decoded:
                continue
            try:
                msg = json.loads(decoded)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "system" and msg.get("session_id"):
                conversation_id = msg["session_id"]

            elif msg_type == "assistant":
                content = msg.get("message", {})
                if isinstance(content, dict):
                    for block in content.get("content", []):
                        if block.get("type") == "text":
                            text = block.get("text", "")
                            delta = text[len(full_text):]
                            if delta:
                                full_text = text
                                print(delta, end="", flush=True)
                        elif block.get("type") == "tool_use":
                            tool_name = block.get("name", "?")
                            print(f"\n  {D}⚡ {tool_name}{X}", flush=True)

            elif msg_type == "content_block_delta":
                delta = msg.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        print(text, end="", flush=True)

            elif msg_type == "result":
                sid = msg.get("session_id")
                if sid:
                    conversation_id = sid
                result_text = msg.get("result", "")
                if result_text and not full_text:
                    print(result_text, end="", flush=True)

        await proc.wait()

        if proc.returncode and proc.returncode != 0:
            stderr = await proc.stderr.read()
            err = stderr.decode().strip()
            if err and not full_text:
                print(f"\n{R}✗ {err[:300]}{X}")

        print()  # newline after streaming

    def show_help():
        print(f"""
  {G}NEXUS Commands{X}

  {R}/gh{X}              GitHub overview
  {R}/gh repos{X}        Your repositories
  {R}/gh prs{X}          Open pull requests
  {R}/gh notifications{X} Notifications

  {R}/sys{X}             System overview
  {R}/sys cpu{X}          CPU per core
  {R}/sys mem{X}          Memory usage
  {R}/sys procs{X}        Top processes
  {R}/sys net{X}          Network info

  {R}/git{X}             Repo status
  {R}/git log{X}          Recent commits
  {R}/git branches{X}     All branches

  {R}/model <id>{X}       Switch model
  {R}clear{X}            Clear screen
  {R}exit{X}             Quit NEXUS
""")

    loop = asyncio.new_event_loop()

    try:
        while True:
            try:
                prompt = input(f"{R}nexus{X} {G}❯{X} ")
            except (EOFError, KeyboardInterrupt):
                print(f"\n  {D}Goodbye.{X}")
                break

            text = prompt.strip()
            if not text:
                continue

            if text in ("exit", "quit"):
                print(f"  {D}Goodbye.{X}")
                break

            if text == "clear":
                os.system("clear" if os.name != "nt" else "cls")
                continue

            if text == "/help":
                show_help()
                continue

            if text.startswith("/model "):
                new_model = text.split(maxsplit=1)[1].strip()
                m = get_model(new_model)
                if m:
                    selected_model = new_model
                    conversation_id = None
                    chat_history = []
                    config = load_config()
                    config["selected_model"] = new_model
                    from nexus_app.config import save_config
                    save_config(config)
                    print(f"  {G}✓{X} Switched to {m.name}")
                else:
                    print(f"  {R}✗{X} Unknown model: {new_model}")
                continue

            # Try plugin commands
            handled = loop.run_until_complete(handle_plugin_command(text))
            if handled:
                continue

            # Send to LLM
            print()
            loop.run_until_complete(run_claude_prompt(text))
            print()

    except Exception as e:
        print(f"\n{R}Error: {e}{X}")
    finally:
        loop.close()


def main():
    parser = argparse.ArgumentParser(
        prog="nexus",
        description="NEXUS — Personal AI Command Center",
    )
    parser.add_argument("directory", nargs="?", default=os.getcwd(),
                        help="Working directory (default: current)")
    parser.add_argument("--inline", "-i", action="store_true",
                        help="Run in current terminal (no window)")
    parser.add_argument("--browser", action="store_true",
                        help="Open in browser instead of native window")
    parser.add_argument("--port", type=int, default=int(os.environ.get("NEXUS_PORT", 7777)),
                        help="Server port (default: 7777)")
    parser.add_argument("--version", action="version",
                        version=f"nexus {__version__}")

    args = parser.parse_args()
    cwd = os.path.abspath(args.directory)
    port = args.port

    # ── Inline mode: run in current terminal ──
    if args.inline:
        run_inline(cwd, port)
        return

    # ── GUI modes: window or browser ──
    print(BANNER.format(version=__version__))
    print(f"  {R}▸{X} Workdir:  {cwd}")
    print(f"  {R}▸{X} Port:     {port}")
    print()

    app = create_app(cwd)

    server_thread = threading.Thread(
        target=start_server, args=(app, HOST, port), daemon=True
    )
    server_thread.start()
    time.sleep(0.5)

    url = f"http://{HOST}:{port}"

    if args.browser:
        import webbrowser
        print(f"  {R}▸{X} Opening in browser...")
        webbrowser.open(url)
        print(f"  {R}▸{X} Running at {url}")
        print(f"  {R}▸{X} Press Ctrl+C to shutdown")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n  {D}Shutting down...{X}")
            sys.exit(0)
    else:
        try:
            import webview
            print(f"  {G}▸{X} Launching native window...")
            print()
            window = webview.create_window(
                title="N E X U S",
                url=url,
                width=1400,
                height=900,
                min_size=(900, 600),
                background_color="#0a0508",
                text_select=True,
            )
            webview.start(debug=False)
            sys.exit(0)
        except ImportError:
            import webbrowser
            print(f"  {R}▸{X} pywebview not found, opening browser...")
            webbrowser.open(url)
            print(f"  {R}▸{X} Running at {url}")
            print(f"  {R}▸{X} Press Ctrl+C to shutdown")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"\n  {D}Shutting down...{X}")
                sys.exit(0)


if __name__ == "__main__":
    main()
