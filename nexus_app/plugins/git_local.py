"""Local Git integration — current repo status, branches, log."""

import asyncio
import shutil

from nexus_app.plugins.base import Plugin


class GitLocalPlugin(Plugin):
    name = "git"
    description = "Local Git repository operations"
    icon = "⎇"
    commands = [
        {"cmd": "/git", "desc": "Repo overview"},
        {"cmd": "/git log", "desc": "Recent commits"},
        {"cmd": "/git branches", "desc": "List branches"},
        {"cmd": "/git diff", "desc": "Show changes"},
        {"cmd": "/git stash", "desc": "List stashes"},
    ]

    def __init__(self, cwd: str):
        self.cwd = cwd
        self._git_bin = shutil.which("git")

    async def is_available(self) -> bool:
        return self._git_bin is not None

    async def _run(self, *args) -> str:
        proc = await asyncio.create_subprocess_exec(
            self._git_bin, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode().strip()

    async def get_status(self) -> dict:
        try:
            branch = await self._run("branch", "--show-current")
            status = await self._run("status", "--porcelain")
            changed = len([l for l in status.splitlines() if l.strip()])
            return {"connected": True, "branch": branch, "changes": changed}
        except Exception:
            return {"connected": False}

    async def get_data(self) -> dict:
        try:
            branch = await self._run("branch", "--show-current")
            status = await self._run("status", "--porcelain")
            changed = len([l for l in status.splitlines() if l.strip()])
            last_commit = await self._run("log", "-1", "--pretty=%s (%ar)")
            return {
                "branch": branch,
                "changes": changed,
                "last_commit": last_commit,
            }
        except Exception:
            return {}

    async def handle_command(self, command: str, args: str) -> str | None:
        if not command.startswith("/git"):
            return None

        full = (command + " " + args).strip()

        if full in ("/git", "/git overview"):
            return await self._overview()
        elif full.startswith("/git log"):
            return await self._log()
        elif full.startswith("/git branches"):
            return await self._branches()
        elif full.startswith("/git diff"):
            return await self._diff()
        elif full.startswith("/git stash"):
            return await self._stashes()
        return None

    async def _overview(self) -> str:
        try:
            branch = await self._run("branch", "--show-current")
            status = await self._run("status", "--short")
            remote = await self._run("remote", "-v")
            last = await self._run("log", "-3", "--oneline")

            return (
                f"**Git Repository**\n\n"
                f"**Branch:** {branch}\n"
                f"**Remote:**\n```\n{remote}\n```\n\n"
                f"**Status:**\n```\n{status or '(clean)'}\n```\n\n"
                f"**Recent:**\n```\n{last}\n```"
            )
        except Exception as e:
            return f"Git error: {e}"

    async def _log(self) -> str:
        raw = await self._run(
            "log", "--oneline", "--graph", "--decorate", "-20"
        )
        return f"**Git Log**\n\n```\n{raw}\n```"

    async def _branches(self) -> str:
        raw = await self._run("branch", "-a", "--sort=-committerdate")
        return f"**Branches**\n\n```\n{raw}\n```"

    async def _diff(self) -> str:
        raw = await self._run("diff", "--stat")
        if not raw:
            raw = "(no changes)"
        return f"**Changes**\n\n```\n{raw}\n```"

    async def _stashes(self) -> str:
        raw = await self._run("stash", "list")
        if not raw:
            return "No stashes."
        return f"**Stashes**\n\n```\n{raw}\n```"
