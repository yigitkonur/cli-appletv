"""👤 User account management commands."""

from __future__ import annotations

import asyncio

import click
from rich import box
from rich.table import Table

from pyatv_cli.connection import connect_device, device_options
from pyatv_cli.output import console, is_json_mode, print_error, print_json, print_success


@click.group()
def accounts():
    """👤 User account management."""


@accounts.command(name="list")
@device_options
def list_accounts(device: str | None, host: str | None) -> None:
    """List available user accounts."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            account_list = await atv.user_accounts.account_list()

            if is_json_mode():
                print_json([
                    {"name": a.name, "id": a.account_id}
                    for a in account_list
                ])
                return

            if not account_list:
                console.print("[dim]No user accounts found.[/]")
                return

            table = Table(
                title="👤 User Accounts",
                box=box.ROUNDED,
                show_lines=True,
            )
            table.add_column("Name", style="bold cyan")
            table.add_column("Account ID", style="yellow")

            for acct in account_list:
                table.add_row(
                    getattr(acct, "name", "—"),
                    getattr(acct, "account_id", str(acct)),
                )

            console.print(table)
        finally:
            atv.close()

    try:
        asyncio.run(_run())
    except ConnectionError as exc:
        print_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        print_error(f"Failed to list accounts: {exc}")


@accounts.command()
@click.argument("account_id")
@device_options
def switch(account_id: str, device: str | None, host: str | None) -> None:
    """Switch to a different user account."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.user_accounts.switch_account(account_id)
            print_success(f"Switched to account: {account_id}")
        finally:
            atv.close()

    try:
        asyncio.run(_run())
    except ConnectionError as exc:
        print_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        print_error(f"Failed to switch account: {exc}")
