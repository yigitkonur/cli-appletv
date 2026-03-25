"""🐚 Interactive Apple TV shell (REPL)."""

from __future__ import annotations

import asyncio

import click

from pyatv_cli.connection import connect_device, device_options
from pyatv_cli.output import console, print_error, print_info, print_success

SHELL_COMMANDS: dict[str, tuple[str, str]] = {
    # Navigation
    "up": ("remote_control", "up"),
    "down": ("remote_control", "down"),
    "left": ("remote_control", "left"),
    "right": ("remote_control", "right"),
    "select": ("remote_control", "select"),
    "menu": ("remote_control", "menu"),
    "home": ("remote_control", "home"),
    # Playback
    "play": ("remote_control", "play"),
    "pause": ("remote_control", "pause"),
    "play-pause": ("remote_control", "play_pause"),
    "stop": ("remote_control", "stop"),
    "next": ("remote_control", "next"),
    "prev": ("remote_control", "previous"),
    # Power
    "power-on": ("power", "turn_on"),
    "power-off": ("power", "turn_off"),
    # Volume
    "vol-up": ("audio", "volume_up"),
    "vol-down": ("audio", "volume_down"),
}


def _print_help() -> None:
    console.print("\n[bold cyan]Available Commands:[/]")
    console.print("  [bold]Navigation:[/]  up, down, left, right, select, menu, home")
    console.print("  [bold]Playback:[/]   play, pause, play-pause, stop, next, prev")
    console.print("  [bold]Power:[/]      power-on, power-off")
    console.print("  [bold]Volume:[/]     vol-up, vol-down, vol <0-100>")
    console.print("  [bold]Apps:[/]       apps, launch <bundle_id>")
    console.print("  [bold]Info:[/]       playing, info, features")
    console.print("  [bold]Other:[/]      help, quit")


async def _handle_cmd(cmd: str, atv) -> bool:  # noqa: ANN001
    """Process a single shell command. Returns False to quit."""
    if not cmd:
        return True
    if cmd in ("quit", "exit", "q"):
        return False
    if cmd == "help":
        _print_help()
        return True

    # -- Now-playing info -------------------------------------------------
    if cmd in ("playing", "info"):
        playing = await atv.metadata.playing()
        console.print(f"  ▶️  [bold]{playing.title or '—'}[/] by {playing.artist or '—'}")
        console.print(f"  📀 {playing.album or '—'} | {playing.device_state}")
        return True

    # -- Volume -----------------------------------------------------------
    if cmd.startswith("vol "):
        try:
            level = float(cmd.split()[1])
            await atv.audio.set_volume(level)
            print_success(f"Volume set to {level}%")
        except (ValueError, IndexError):
            print_error("Usage: vol <0-100>")
        return True

    # -- App launcher -----------------------------------------------------
    if cmd.startswith("launch "):
        bundle_id = cmd.split(None, 1)[1]
        await atv.apps.launch_app(bundle_id)
        print_success(f"Launched {bundle_id}")
        return True

    # -- App list ---------------------------------------------------------
    if cmd == "apps":
        app_list = await atv.apps.app_list()
        for app in app_list:
            console.print(f"  📱 {app.name} [dim]({app.identifier})[/]")
        return True

    # -- Features ---------------------------------------------------------
    if cmd == "features":
        features = atv.features.all_features()
        for feat, info in sorted(features.items(), key=lambda x: x[0].name):
            icon = "🟢" if "Available" in str(info.state) else "🔴"
            console.print(f"  {icon} {feat.name}")
        return True

    # -- Mapped remote/power/audio commands -------------------------------
    if cmd in SHELL_COMMANDS:
        iface_name, method_name = SHELL_COMMANDS[cmd]
        iface = getattr(atv, iface_name)
        method = getattr(iface, method_name)
        await method()
        print_success(f"Sent: {cmd}")
        return True

    print_error(f"Unknown command: {cmd}. Type 'help' for available commands.")
    return True


@click.command()
@device_options
def shell(device: str | None, host: str | None) -> None:
    """🐚 Interactive Apple TV shell."""

    async def _run() -> None:
        print_info("Connecting to Apple TV…")
        atv = await connect_device(device, host)

        console.print("[bold cyan]╭────────────────────────────────────────────────╮[/]")
        console.print("[bold cyan]│[/]  🍎 Apple TV Interactive Shell                [bold cyan]│[/]")
        console.print("[bold cyan]│[/]  Type 'help' for commands, 'quit' to exit     [bold cyan]│[/]")
        console.print("[bold cyan]╰────────────────────────────────────────────────╯[/]")

        try:
            while True:
                try:
                    cmd = input("\n🍎 atv> ").strip().lower()
                except EOFError:
                    break

                try:
                    if not await _handle_cmd(cmd, atv):
                        break
                except Exception as exc:  # noqa: BLE001
                    print_error(f"Command failed: {exc}")
        finally:
            atv.close()
            print_info("Disconnected.")

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print()
    except ConnectionError as exc:
        print_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        print_error(f"Shell error: {exc}")
