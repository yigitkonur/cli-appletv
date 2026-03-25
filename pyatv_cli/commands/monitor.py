"""📡 Live push-update monitoring with Rich Live display."""

from __future__ import annotations

import asyncio

import click
from rich import box
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from pyatv_cli.connection import connect_device, device_options
from pyatv_cli.output import console, print_error, print_info


class PushMonitor:
    """Handles push update events and maintains display state."""

    def __init__(self) -> None:
        self.current_state: dict[str, str] = {}
        self.update_count: int = 0

    # -- pyatv push listener interface ------------------------------------

    def playstatus_update(self, updater, playing) -> None:  # noqa: ANN001
        self.update_count += 1
        self.current_state = {
            "title": playing.title or "—",
            "artist": playing.artist or "—",
            "album": playing.album or "—",
            "state": str(playing.device_state),
            "media_type": str(playing.media_type),
            "position": self._fmt_time(playing.position),
            "total_time": self._fmt_time(playing.total_time),
            "shuffle": str(playing.shuffle) if playing.shuffle else "—",
            "repeat": str(playing.repeat) if playing.repeat else "—",
        }

    def playstatus_error(self, updater, exception) -> None:  # noqa: ANN001
        self.current_state["error"] = str(exception)

    # -- rendering --------------------------------------------------------

    _STATE_EMOJI: dict[str, str] = {
        "Playing": "▶️",
        "Paused": "⏸️",
        "Idle": "⏹️",
        "Loading": "⏳",
    }

    def render(self) -> Panel:
        if not self.current_state:
            return Panel(
                "Waiting for updates…",
                title="📡 Monitor",
                border_style="yellow",
            )

        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")

        raw_state = self.current_state.get("state", "")
        short = raw_state.split(".")[-1] if "." in raw_state else raw_state
        emoji = self._STATE_EMOJI.get(short, "❓")

        table.add_row("State", f"{emoji} {raw_state}")
        table.add_row("Title", self.current_state.get("title", "—"))
        table.add_row("Artist", self.current_state.get("artist", "—"))
        table.add_row("Album", self.current_state.get("album", "—"))
        table.add_row(
            "Progress",
            f"{self.current_state.get('position', '—')} / "
            f"{self.current_state.get('total_time', '—')}",
        )
        table.add_row("Type", self.current_state.get("media_type", "—"))
        table.add_row("Shuffle", self.current_state.get("shuffle", "—"))
        table.add_row("Repeat", self.current_state.get("repeat", "—"))
        table.add_row("Updates", str(self.update_count))

        if "error" in self.current_state:
            table.add_row("Error", f"[red]{self.current_state['error']}[/]")

        return Panel(
            table,
            title="📡 Live Monitor",
            border_style="green",
            box=box.ROUNDED,
        )

    @staticmethod
    def _fmt_time(seconds: float | int | None) -> str:
        if seconds is None:
            return "—"
        total = int(seconds)
        m, s = divmod(total, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


@click.command()
@device_options
def monitor(device: str | None, host: str | None) -> None:
    """📡 Live monitoring of playback status."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            mon = PushMonitor()
            atv.push_updater.listener = mon
            atv.push_updater.start()

            print_info("Monitoring started. Press Ctrl+C to stop.")

            with Live(mon.render(), console=console, refresh_per_second=2) as live:
                try:
                    while True:
                        live.update(mon.render())
                        await asyncio.sleep(0.5)
                except KeyboardInterrupt:
                    pass

            atv.push_updater.stop()
            print_info("Monitoring stopped.")
        finally:
            atv.close()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
    except ConnectionError as exc:
        print_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        print_error(f"Monitor error: {exc}")
