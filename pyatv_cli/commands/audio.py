"""🔊 Audio and volume control commands."""

from __future__ import annotations

import click
from rich.progress import BarColumn, Progress, TextColumn

from pyatv_cli.connection import connect_device, device_options, run_async
from pyatv_cli.output import (
    console,
    is_json_mode,
    make_table,
    print_error,
    print_json,
    print_kv,
    print_success,
)


@click.group()
def audio():
    """🔊 Audio and volume control."""
    pass


@audio.command()
@device_options
def get(device: str | None, host: str | None) -> None:
    """Show current volume level."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            volume = atv.audio.volume

            if is_json_mode():
                print_json({"volume": volume})
                return

            console.print(f"🔊 Volume: {volume:.0f}%")
            with Progress(
                TextColumn("[bold blue]"),
                BarColumn(bar_width=40, complete_style="green", finished_style="green"),
                TextColumn(f"[bold]{volume:.0f}/100[/bold]"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("volume", total=100, completed=volume)
                # Force a final render so the bar is visible
                progress.refresh()
            # Rich transient clears the bar; re-print a static version
            filled = int(volume / 100 * 40)
            bar = "█" * filled + "░" * (40 - filled)
            console.print(f"[green][{bar}][/green] {volume:.0f}/100")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@audio.command(name="set")
@click.argument("level", type=click.FloatRange(0, 100))
@device_options
def set_volume(level: float, device: str | None, host: str | None) -> None:
    """Set volume level (0-100)."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.audio.set_volume(level)
            print_success(f"Volume set to {level:.0f}%")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@audio.command()
@device_options
def up(device: str | None, host: str | None) -> None:
    """Increase volume."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.audio.volume_up()
            print_success("Volume increased")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@audio.command()
@device_options
def down(device: str | None, host: str | None) -> None:
    """Decrease volume."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.audio.volume_down()
            print_success("Volume decreased")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@audio.command()
@device_options
def devices(device: str | None, host: str | None) -> None:
    """List audio output devices."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            output_devices = atv.audio.output_devices

            if is_json_mode():
                print_json([
                    {
                        "name": d.name,
                        "identifier": d.identifier,
                        "is_selected": d.is_selected,
                    }
                    for d in output_devices
                ])
                return

            if not output_devices:
                console.print("[dim]No audio output devices found.[/dim]")
                return

            table = make_table("🔊 Audio Output Devices", [
                ("Name", "bold cyan"),
                ("Identifier", "yellow"),
                ("Selected", "green"),
            ])
            for d in output_devices:
                selected = "✓" if d.is_selected else ""
                table.add_row(d.name, d.identifier, selected)

            console.print(table)
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)
