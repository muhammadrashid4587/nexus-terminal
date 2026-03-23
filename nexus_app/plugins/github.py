"""GitHub integration — repos, PRs, issues, activity feed."""

import asyncio
import json
import shutil

from nexus_app.plugins.base import Plugin


class GitHubPlugin(Plugin):
    name = "github"
    description = "GitHub repos, PRs, issues, activity"
    icon = "⬡"
    commands = [
        {"cmd": "/gh", "desc": "GitHub overview"},
        {"cmd": "/gh repos", "desc": "Your repositories"},
        {"cmd": "/gh prs", "desc": "Open pull requests"},
        {"cmd": "/gh issues", "desc": "Open issues"},
        {"cmd": "/gh activity", "desc": "Recent activity"},
        {"cmd": "/gh notifications", "desc": "Notifications"},
    ]

    def __init__(self):
        self._gh_bin = shutil.which("gh")

    async def is_available(self) -> bool:
        return self._gh_bin is not None

    async def _run_gh(self, *args) -> str:
        proc = await asyncio.create_subprocess_exec(
            self._gh_bin, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(stderr.decode().strip()[:200])
        return stdout.decode().strip()

    async def get_status(self) -> dict:
        try:
            user = await self._run_gh("api", "user", "--jq", ".login")
            return {"connected": True, "user": user}
        except Exception:
            return {"connected": False}

    async def get_data(self) -> dict:
        """Get dashboard data: recent repos, PR count, notification count."""
        data = {}
        try:
            # Notification count
            notifs = await self._run_gh("api", "notifications", "--jq", "length")
            data["notifications"] = int(notifs) if notifs.isdigit() else 0
        except Exception:
            data["notifications"] = 0

        try:
            # Open PR count across your repos
            prs = await self._run_gh(
                "search", "prs", "--author=@me", "--state=open",
                "--json", "number", "--jq", "length"
            )
            data["open_prs"] = int(prs) if prs.isdigit() else 0
        except Exception:
            data["open_prs"] = 0

        return data

    async def handle_command(self, command: str, args: str) -> str | None:
        if not command.startswith("/gh"):
            return None

        full = (command + " " + args).strip()

        if full in ("/gh", "/gh overview"):
            return await self._overview()
        elif full.startswith("/gh repos"):
            return await self._repos()
        elif full.startswith("/gh prs"):
            return await self._prs()
        elif full.startswith("/gh issues"):
            return await self._issues()
        elif full.startswith("/gh activity"):
            return await self._activity()
        elif full.startswith("/gh notifications"):
            return await self._notifications()
        return None

    async def _overview(self) -> str:
        try:
            user_json = await self._run_gh("api", "user")
            user = json.loads(user_json)
            name = user.get("login", "?")
            repos = user.get("public_repos", 0) + user.get("total_private_repos", 0)
            followers = user.get("followers", 0)

            notifs = await self._run_gh("api", "notifications", "--jq", "length")

            return (
                f"**GitHub: @{name}**\n"
                f"Repos: {repos}  |  Followers: {followers}  |  Notifications: {notifs}\n\n"
                f"Use `/gh repos`, `/gh prs`, `/gh issues`, `/gh activity` for details."
            )
        except Exception as e:
            return f"GitHub error: {e}"

    async def _repos(self) -> str:
        try:
            raw = await self._run_gh(
                "repo", "list", "--limit", "15", "--json",
                "name,description,updatedAt,isPrivate,stargazerCount",
            )
            repos = json.loads(raw)
            lines = ["**Your Repositories** (recent 15)\n"]
            for r in repos:
                vis = "🔒" if r.get("isPrivate") else "  "
                stars = f"★{r.get('stargazerCount', 0)}" if r.get('stargazerCount') else ""
                desc = r.get("description", "") or ""
                if len(desc) > 50:
                    desc = desc[:50] + "..."
                lines.append(f"{vis} **{r['name']}** {stars}  {desc}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    async def _prs(self) -> str:
        try:
            raw = await self._run_gh(
                "search", "prs", "--author=@me", "--state=open",
                "--json", "title,repository,number,updatedAt",
                "--limit", "15",
            )
            prs = json.loads(raw)
            if not prs:
                return "No open pull requests."
            lines = [f"**Open PRs** ({len(prs)})\n"]
            for pr in prs:
                repo = pr.get("repository", {}).get("name", "?")
                lines.append(f"  #{pr['number']} **{pr['title']}** ({repo})")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    async def _issues(self) -> str:
        try:
            raw = await self._run_gh(
                "search", "issues", "--author=@me", "--state=open",
                "--json", "title,repository,number",
                "--limit", "15",
            )
            issues = json.loads(raw)
            if not issues:
                return "No open issues."
            lines = [f"**Open Issues** ({len(issues)})\n"]
            for iss in issues:
                repo = iss.get("repository", {}).get("name", "?")
                lines.append(f"  #{iss['number']} **{iss['title']}** ({repo})")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    async def _activity(self) -> str:
        try:
            raw = await self._run_gh(
                "api", "users/{owner}/events", "--jq",
                '.[:10] | .[] | "\\(.type) \\(.repo.name) \\(.created_at[:10])"'
            )
            if not raw:
                return "No recent activity."
            return f"**Recent Activity**\n\n```\n{raw}\n```"
        except Exception as e:
            return f"Error: {e}"

    async def _notifications(self) -> str:
        try:
            raw = await self._run_gh(
                "api", "notifications", "--jq",
                '.[:15] | .[] | "\\(.subject.type): \\(.subject.title) (\\(.repository.name))"'
            )
            if not raw:
                return "No notifications."
            return f"**Notifications**\n\n{raw}"
        except Exception as e:
            return f"Error: {e}"
