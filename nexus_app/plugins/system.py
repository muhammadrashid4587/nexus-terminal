"""System monitoring — CPU, memory, disk, network, processes."""

import platform
import asyncio

from nexus_app.plugins.base import Plugin


class SystemPlugin(Plugin):
    name = "system"
    description = "System monitoring and stats"
    icon = "◈"
    commands = [
        {"cmd": "/sys", "desc": "System overview"},
        {"cmd": "/sys cpu", "desc": "CPU usage"},
        {"cmd": "/sys mem", "desc": "Memory usage"},
        {"cmd": "/sys disk", "desc": "Disk usage"},
        {"cmd": "/sys procs", "desc": "Top processes"},
        {"cmd": "/sys net", "desc": "Network info"},
    ]

    async def is_available(self) -> bool:
        try:
            import psutil
            return True
        except ImportError:
            return False

    async def get_status(self) -> dict:
        import psutil
        return {
            "connected": True,
            "cpu": psutil.cpu_percent(interval=0.1),
            "mem": psutil.virtual_memory().percent,
        }

    async def get_data(self) -> dict:
        import psutil
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "mem_percent": vm.percent,
            "mem_used_gb": round(vm.used / (1024**3), 1),
            "mem_total_gb": round(vm.total / (1024**3), 1),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
        }

    async def handle_command(self, command: str, args: str) -> str | None:
        if not command.startswith("/sys"):
            return None

        full = (command + " " + args).strip()

        if full in ("/sys", "/sys overview"):
            return await self._overview()
        elif full.startswith("/sys cpu"):
            return await self._cpu()
        elif full.startswith("/sys mem"):
            return await self._mem()
        elif full.startswith("/sys disk"):
            return await self._disk()
        elif full.startswith("/sys procs"):
            return await self._procs()
        elif full.startswith("/sys net"):
            return await self._net()
        return None

    async def _overview(self) -> str:
        import psutil

        uname = platform.uname()
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = psutil.boot_time()

        import datetime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot)
        hours = int(uptime.total_seconds() // 3600)
        mins = int((uptime.total_seconds() % 3600) // 60)

        return (
            f"**System Overview**\n\n"
            f"**Host:** {uname.node}\n"
            f"**OS:** {uname.system} {uname.release}\n"
            f"**Arch:** {uname.machine}\n"
            f"**Python:** {platform.python_version()}\n"
            f"**Uptime:** {hours}h {mins}m\n\n"
            f"**CPU:** {psutil.cpu_percent()}% ({psutil.cpu_count()} cores)\n"
            f"**Memory:** {vm.percent}% ({vm.used // (1024**3)}/{vm.total // (1024**3)} GB)\n"
            f"**Disk:** {disk.percent}% ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)\n"
        )

    async def _cpu(self) -> str:
        import psutil
        per_cpu = psutil.cpu_percent(interval=0.5, percpu=True)
        bars = []
        for i, pct in enumerate(per_cpu):
            filled = int(pct / 5)
            bar = "█" * filled + "░" * (20 - filled)
            bars.append(f"  Core {i:2d}: [{bar}] {pct:5.1f}%")
        return f"**CPU Usage**\n\n" + "\n".join(bars)

    async def _mem(self) -> str:
        import psutil
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return (
            f"**Memory**\n\n"
            f"RAM:  {vm.used/(1024**3):.1f} / {vm.total/(1024**3):.1f} GB ({vm.percent}%)\n"
            f"Swap: {swap.used/(1024**3):.1f} / {swap.total/(1024**3):.1f} GB ({swap.percent}%)\n"
            f"Available: {vm.available/(1024**3):.1f} GB\n"
        )

    async def _disk(self) -> str:
        import psutil
        partitions = psutil.disk_partitions()
        lines = ["**Disk Usage**\n"]
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                lines.append(
                    f"  {p.mountpoint}: {usage.used/(1024**3):.1f}/{usage.total/(1024**3):.1f} GB "
                    f"({usage.percent}%)"
                )
            except PermissionError:
                pass
        return "\n".join(lines)

    async def _procs(self) -> str:
        import psutil
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
        lines = ["**Top Processes (by CPU)**\n"]
        lines.append(f"  {'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  NAME")
        for p in procs[:15]:
            lines.append(
                f"  {p.get('pid', 0):>7}  {p.get('cpu_percent', 0):>5.1f}%  "
                f"{p.get('memory_percent', 0):>5.1f}%  {p.get('name', '?')}"
            )
        return "\n".join(lines)

    async def _net(self) -> str:
        import psutil
        net = psutil.net_io_counters()
        addrs = psutil.net_if_addrs()
        lines = ["**Network**\n"]
        lines.append(f"  Sent:     {net.bytes_sent/(1024**3):.2f} GB")
        lines.append(f"  Received: {net.bytes_recv/(1024**3):.2f} GB")
        lines.append(f"  Packets:  {net.packets_sent:,} sent / {net.packets_recv:,} recv\n")

        for iface, addr_list in addrs.items():
            for addr in addr_list:
                if addr.family.name == 'AF_INET':
                    lines.append(f"  {iface}: {addr.address}")
                    break
        return "\n".join(lines)
