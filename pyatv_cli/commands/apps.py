"""📱 App management commands."""

from __future__ import annotations

import click

from pyatv_cli.connection import connect_device, device_options, run_async
from pyatv_cli.output import (
    console,
    is_json_mode,
    make_table,
    print_error,
    print_json,
    print_success,
)


@click.group()
def apps():
    """📱 App management."""
    pass


@apps.command(name="list")
@device_options
def list_apps(device: str | None, host: str | None) -> None:
    """List all installed apps."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            app_list = await atv.apps.app_list()

            if is_json_mode():
                print_json([
                    {"name": a.name, "identifier": a.identifier}
                    for a in app_list
                ])
                return

            if not app_list:
                console.print("[dim]No apps found.[/dim]")
                return

            table = make_table("📱 Installed Apps", [
                ("Name", "bold cyan"),
                ("Bundle ID", "yellow"),
            ])
            for a in app_list:
                table.add_row(a.name, a.identifier)

            console.print(table)
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@apps.command()
@click.argument("bundle_id")
@device_options
def launch(bundle_id: str, device: str | None, host: str | None) -> None:
    """Launch an app by bundle ID or URL."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.apps.launch_app(bundle_id)
            print_success(f"Launched {bundle_id}")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)
