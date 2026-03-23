#!/usr/bin/env python3
"""
N E X U S  —  CLI Entry Point
"""

import argparse
import asyncio
import json
import os
import socket
import sys
import threading
import time

from nexus_app import __version__

# ── Colors ──
R = "\033[38;2;255;26;26m"
G = "\033[38;2;255;215;0m"
D = "\033[2m"
B = "\033[1m"
X = "\033[0m"

BANNER = f"""{R}
  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
{X}
  {D}Neural Execution & Unified System  v{__version__}{X}
  {D}Personal AI Command Center{X}
"""

HOST = "127.0.0.1"


def find_free_port(start=7777):
    """Find a free port starting from `start`."""
    for port in range(start, start + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, port))
                return port
        except OSError:
            continue
    return start + 100


def first_run_setup():
    """Interactive first-run onboarding. Returns config dict."""
    from nexus_app.config import load_config, save_config

    config = load_config()

    # Check if already set up
    owner = config.get("owner", {})
    if owner.get("full_name") and owner.get("title"):
        return config

    print()
    print(f"  {G}━━━ Welcome to NEXUS ━━━{X}")
    print(f"  {D}First-time setup. This only happens once.{X}")
    print()

    # Get name
    full_name = ""
    while not full_name:
        try:
            full_name = input(f"  {R}▸{X} Your full name: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {D}Setup cancelled.{X}")
            sys.exit(0)

    # Get gender for title
    print()
    print(f"  {D}How should NEXUS greet you?{X}")
    print(f"    {G}1{X}  Mr. {full_name}")
    print(f"    {G}2{X}  Ms. {full_name}")
    print(f"    {G}3{X}  Dr. {full_name}")
    print(f"    {G}4{X}  Just {full_name}")
    print()

    choice = ""
    while choice not in ("1", "2", "3", "4"):
        try:
            choice = input(f"  {R}▸{X} Choose (1-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "4"

    titles = {"1": "Mr.", "2": "Ms.", "3": "Dr.", "4": ""}
    title = titles[choice]

    greeting = f"{title} {full_name}".strip()

    # Save
    config["owner"] = {
        "full_name": full_name,
        "title": title,
        "greeting": greeting,
    }
    save_config(config)

    print()
    print(f"  {G}✓{X} Hello, {R}{greeting}{X}. NEXUS is yours.")
    print()
    time.sleep(1)

    return config


def ask_launch_mode():
    """Ask user how they want to launch NEXUS."""
    print(f"  {D}How do you want to run NEXUS?{X}")
    print()
    print(f"    {G}1{X}  {B}Inline{X}     — right here in this terminal")
    print(f"    {G}2{X}  {B}Window{X}     — open a new native window")
    print(f"    {G}3{X}  {B}Browser{X}    — open in your browser")
    print()

    choice = ""
    while choice not in ("1", "2", "3"):
        try:
            choice = input(f"  {R}▸{X} Choose (1-3): ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {D}Goodbye.{X}")
            sys.exit(0)

    return {"1": "inline", "2": "window", "3": "browser"}[choice]


def start_server(app, host, port):
    """Run server in background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    from aiohttp import web
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, host, port)
    loop.run_until_complete(site.start())
    loop.run_forever()


def run_inline(cwd: str, config: dict):
    """Run NEXUS in the current terminal — all models via API."""
    from nexus_app.config import load_config, save_config
    from nexus_app.providers import get_model, stream_api_response
    from nexus_app.plugins.base import PluginManager
    from nexus_app.plugins.github import GitHubPlugin
    from nexus_app.plugins.system import SystemPlugin
    from nexus_app.plugins.git_local import GitLocalPlugin

    plugins = PluginManager()
    plugins.register(GitHubPlugin())
    plugins.register(SystemPlugin())
    plugins.register(GitLocalPlugin(cwd))

    selected_model = config.get("selected_model", "claude-opus")
    chat_history = []
    greeting = config.get("owner", {}).get("greeting", "Operator")

    print()
    print(f"  {R}▸{X} Mode:     {G}INLINE TERMINAL{X}")
    print(f"  {R}▸{X} Workdir:  {cwd}")
    print(f"  {R}▸{X} Model:    {selected_model}")
    print()
    print(f"  {G}HELLO {R}{greeting.upper()}{X}")
    print(f"  {D}Type /help for commands, exit to quit{X}")
    print()

    async def handle_plugin_command(text):
        if not text.startswith("/"):
            return False
        parts = text.split(maxsplit=1)
        cmd, args = parts[0], parts[1] if len(parts) > 1 else ""
        result = await plugins.handle_command(cmd, args)
        if result is not None:
            print(f"\n{result}\n")
            return True
        return False

    async def run_prompt(prompt):
        nonlocal chat_history
        model = get_model(selected_model) or get_model("claude-opus")

        chat_history.append({"role": "user", "content": prompt})
        messages = [
            {"role": "system", "content": f"You are NEXUS, an advanced AI coding assistant. Working dir: {cwd}"},
            *chat_history,
        ]

        try:
            full_response = ""

            async def on_chunk(text):
                nonlocal full_response
                full_response += text
                print(text, end="", flush=True)

            await stream_api_response(model, messages, on_chunk)

            if full_response:
                chat_history.append({"role": "assistant", "content": full_response})
            if len(chat_history) > 40:
                chat_history = chat_history[-30:]

        except Exception as e:
            print(f"\n  {R}✗ {e}{X}")

        print()

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
                print(f"\n  {D}Goodbye, {greeting}.{X}")
                break
            text = prompt.strip()
            if not text:
                continue
            if text in ("exit", "quit"):
                print(f"  {D}Goodbye, {greeting}.{X}")
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
                    cfg = load_config()
                    cfg["selected_model"] = new_model
                    save_config(cfg)
                    print(f"  {G}✓{X} Switched to {m.name}")
                else:
                    print(f"  {R}✗{X} Unknown model: {new_model}")
                continue
            handled = loop.run_until_complete(handle_plugin_command(text))
            if handled:
                continue
            print()
            loop.run_until_complete(run_prompt(text))
            print()
    except Exception as e:
        print(f"\n  {R}Error: {e}{X}")
    finally:
        loop.close()


def run_gui(cwd: str, port: int, mode: str, config: dict):
    """Run NEXUS in window or browser mode."""
    from nexus_app.server import create_app

    greeting = config.get("owner", {}).get("greeting", "Operator")

    # Update the app's greeting
    app = create_app(cwd)

    port = find_free_port(port)

    print(f"  {R}▸{X} Port:     {port}")
    print()

    server_thread = threading.Thread(
        target=start_server, args=(app, HOST, port), daemon=True
    )
    server_thread.start()
    time.sleep(0.8)

    url = f"http://{HOST}:{port}"

    if mode == "browser":
        import webbrowser
        print(f"  {R}▸{X} Opening in browser...")
        webbrowser.open(url)
        print(f"  {R}▸{X} Running at {url}")
        print(f"  {R}▸{X} Press Ctrl+C to shutdown")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n  {D}Goodbye, {greeting}.{X}")
            sys.exit(0)
    else:
        # Native window
        try:
            import webview
            print(f"  {G}▸{X} Launching native window...")
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
            # Fallback to browser
            import webbrowser
            print(f"  {G}▸{X} Opening in browser (pywebview not available)...")
            webbrowser.open(url)
            print(f"  {R}▸{X} Running at {url}")
            print(f"  {R}▸{X} Press Ctrl+C to shutdown")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"\n  {D}Goodbye, {greeting}.{X}")
                sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="nexus",
        description="NEXUS — Personal AI Command Center",
    )
    parser.add_argument("directory", nargs="?", default=os.getcwd(),
                        help="Working directory (default: current)")
    parser.add_argument("--inline", "-i", action="store_true",
                        help="Run in current terminal (no window)")
    parser.add_argument("--browser", "-b", action="store_true",
                        help="Open in browser")
    parser.add_argument("--window", "-w", action="store_true",
                        help="Open native window")
    parser.add_argument("--port", type=int, default=int(os.environ.get("NEXUS_PORT", 7777)),
                        help="Server port (default: 7777)")
    parser.add_argument("--version", action="version",
                        version=f"nexus {__version__}")
    parser.add_argument("--reset", action="store_true",
                        help="Reset config and re-run setup")

    args = parser.parse_args()
    cwd = os.path.abspath(args.directory)

    # ── Suppress ugly tracebacks ──
    sys.tracebacklimit = 0

    # ── Banner ──
    print(BANNER)

    # ── First-run setup or reset ──
    if args.reset:
        from nexus_app.config import save_config, DEFAULT_CONFIG
        save_config(DEFAULT_CONFIG)

    config = first_run_setup()
    greeting = config.get("owner", {}).get("greeting", "Operator")

    print(f"  {R}▸{X} Workdir:  {cwd}")

    # ── Determine mode ──
    if args.inline:
        mode = "inline"
    elif args.browser:
        mode = "browser"
    elif args.window:
        mode = "window"
    else:
        # Ask interactively
        mode = ask_launch_mode()

    print()

    # ── Launch ──
    if mode == "inline":
        run_inline(cwd, config)
    else:
        run_gui(cwd, args.port, mode, config)


if __name__ == "__main__":
    main()
