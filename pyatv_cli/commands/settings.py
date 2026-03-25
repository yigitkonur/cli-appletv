"""⚙️  Device settings commands."""

from __future__ import annotations

import asyncio

import click
from rich import box
from rich.table import Table

from pyatv_cli.connection import connect_device, device_options
from pyatv_cli.output import console, is_json_mode, print_error, print_json, print_success


@click.group()
def settings():
    """⚙️  Device settings."""


@settings.command()
@device_options
def show(device: str | None, host: str | None) -> None:
    """Show all device settings."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            info = atv.settings.info

            if is_json_mode():
                data = info.model_dump() if hasattr(info, "model_dump") else vars(info)
                print_json({str(k): str(v) for k, v in data.items()})
                return

            data = info.model_dump() if hasattr(info, "model_dump") else vars(info)
            table = Table(
                title="⚙️  Device Settings",
                box=box.ROUNDED,
                show_lines=True,
            )
            table.add_column("Key", style="bold cyan")
            table.add_column("Value", style="yellow")

            for key, value in sorted(data.items(), key=lambda x: str(x[0])):
                table.add_row(str(key), str(value))

            console.print(table)
        finally:
            atv.close()

    try:
        asyncio.run(_run())
    except ConnectionError as exc:
        print_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        print_error(f"Failed to show settings: {exc}")


@settings.command(name="set")
@click.argument("key")
@click.argument("value")
@device_options
def set_setting(key: str, value: str, device: str | None, host: str | None) -> None:
    """Set a device setting (KEY VALUE)."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.settings.change_setting(key, value)
            print_success(f"Setting '{key}' set to '{value}'")
        finally:
            atv.close()

    try:
        asyncio.run(_run())
    except ConnectionError as exc:
        print_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        print_error(f"Failed to set '{key}': {exc}")


@settings.command()
@click.argument("key")
@device_options
def remove(key: str, device: str | None, host: str | None) -> None:
    """Remove a device setting."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.settings.remove_setting(key)
            print_success(f"Setting '{key}' removed")
        finally:
            atv.close()

    try:
        asyncio.run(_run())
    except ConnectionError as exc:
        print_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        print_error(f"Failed to remove '{key}': {exc}")
