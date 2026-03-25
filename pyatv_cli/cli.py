"""Main CLI entry point for pyatv-cli."""
import click
import asyncio
import sys

import pyatv
from pyatv.const import Protocol

from pyatv_cli.config import (
    load_config, save_config, add_device, set_credentials,
    set_default, remove_device, list_devices, get_device,
)
from pyatv_cli.connection import PROTOCOL_MAP
from pyatv_cli.output import (
    console, set_json_mode, print_success, print_error,
    print_warning, print_info, print_device_table,
    print_panel, print_json, is_json_mode, make_table,
)

from pyatv_cli.commands.power import power
from pyatv_cli.commands.remote import remote
from pyatv_cli.commands.media import media
from pyatv_cli.commands.apps import apps
from pyatv_cli.commands.audio import audio
from pyatv_cli.commands.keyboard import keyboard
from pyatv_cli.commands.touch import touch
from pyatv_cli.commands.stream import stream
from pyatv_cli.commands.system import system
from pyatv_cli.commands.accounts import accounts
from pyatv_cli.commands.monitor import monitor
from pyatv_cli.commands.settings import settings
from pyatv_cli.commands.shell import shell


BANNER = """[bold cyan]
   ╭─────────────────────────────────────────╮
   │  🍎  pyatv-cli · Apple TV Remote  v1.0  │
   │     Control your Apple TV from the CLI   │
   ╰─────────────────────────────────────────╯[/]"""


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output in JSON format for scripting.")
@click.version_option(package_name="cli-appletv", prog_name="atv")
@click.pass_context
def cli(ctx, json_mode):
    """🍎 pyatv-cli — Comprehensive Apple TV remote control.

    Control your Apple TV entirely from the command line.
    Supports power, remote, apps, media, audio, streaming, and more.

    \b
    Quick start:
      atv scan              Discover Apple TVs on your network
      atv pair              Pair with a discovered device
      atv power status      Check if your Apple TV is on
      atv remote play       Send play command
      atv media info        See what's playing
      atv shell             Interactive remote control
    """
    set_json_mode(json_mode)
    if ctx.invoked_subcommand is None:
        if json_mode:
            ctx.invoke(status_cmd)
        else:
            # Default to TUI when no subcommand
            from pyatv_cli.tui.app import run_tui
            run_tui()


# ─── Register command groups ────────────────────────────────────────

cli.add_command(power)
cli.add_command(remote)
cli.add_command(media)
cli.add_command(apps)
cli.add_command(audio)
cli.add_command(keyboard)
cli.add_command(touch)
cli.add_command(stream)
cli.add_command(system)
cli.add_command(accounts)
cli.add_command(monitor)
cli.add_command(settings)
cli.add_command(shell)


# ─── TUI command ───────────────────────────────────────────────


@cli.command()
@click.option("--device", "-d", default=None, help="Device identifier.")
@click.option("--host", default=None, help="Device IP address.")
def tui(device, host):
    """🖥️  Launch interactive TUI remote control."""
    from pyatv_cli.tui.app import run_tui
    run_tui(device=device, host=host)


# ─── Top-level commands ────────────────────────────────────────────


@cli.command()
@click.option("--timeout", "-t", type=int, default=5, help="Scan timeout in seconds.")
@click.option("--host", help="Scan a specific IP address.")
def scan(timeout, host):
    """🔍 Discover Apple TVs on the network."""
    async def _run():
        print_info(f"Scanning for Apple TVs (timeout: {timeout}s)...")
        scan_kwargs = {"timeout": timeout}
        if host:
            scan_kwargs["hosts"] = [host]
        devices = await pyatv.scan(asyncio.get_event_loop(), **scan_kwargs)
        if not devices:
            print_warning("No Apple TVs found. Make sure your device is on the same network.")
            return
        if is_json_mode():
            result = []
            for d in devices:
                dev = {
                    "name": d.name,
                    "address": str(d.address),
                    "identifier": d.identifier,
                    "model": d.device_info.model_str or "Unknown",
                    "os": str(d.device_info.operating_system),
                    "version": d.device_info.version or "",
                    "services": [str(s.protocol) for s in d.services],
                }
                result.append(dev)
            print_json(result)
        else:
            print_device_table(devices)
            console.print(f"\n[dim]Found {len(devices)} device(s). Use [bold]atv pair[/bold] to pair.[/dim]")
    asyncio.run(_run())


@cli.command()
@click.option("--protocol", "-p", type=click.Choice(list(PROTOCOL_MAP.keys())), default="companion",
              help="Protocol to pair (default: companion).")
@click.option("--id", "identifier", help="Device identifier to pair with.")
@click.option("--host", help="Device IP address.")
def pair(protocol, identifier, host):
    """🔗 Pair with an Apple TV."""
    async def _run():
        print_info(f"Scanning for Apple TV...")
        scan_kwargs = {"timeout": 5}
        if identifier:
            scan_kwargs["identifier"] = identifier
        if host:
            scan_kwargs["hosts"] = [host]

        devices = await pyatv.scan(asyncio.get_event_loop(), **scan_kwargs)
        if not devices:
            print_error("No Apple TV found. Run 'atv scan' first.")
            return

        # If multiple devices found and no identifier, let user pick
        if len(devices) > 1 and not identifier:
            print_device_table(devices)
            console.print("\n[bold]Multiple devices found. Use --id to specify one.[/bold]")
            return

        device = devices[0]
        proto = PROTOCOL_MAP[protocol]
        print_info(f"Pairing with [bold]{device.name}[/] via {protocol}...")

        pairing = await pyatv.pair(device, proto, asyncio.get_event_loop())
        try:
            await pairing.begin()

            if pairing.device_provides_pin:
                console.print("\n[bold yellow]📺 Check your Apple TV — a PIN code should be displayed.[/]")
                pin = click.prompt("Enter the 4-digit PIN", type=str)
                pairing.pin(int(pin))
            elif pairing.has_paired:
                print_info("No PIN required for this protocol.")
            else:
                pin = click.prompt("Enter PIN for pairing", type=str)
                pairing.pin(int(pin))

            await pairing.finish()

            if pairing.has_paired:
                credentials = pairing.service.credentials
                config = load_config()
                add_device(config, device.identifier, device.name, str(device.address))
                set_credentials(config, device.identifier, protocol, credentials)

                # Auto-set as default if no default exists
                if not config.get("default_device"):
                    set_default(config, device.identifier)

                save_config(config)
                print_success(f"Paired with {device.name} via {protocol}!")
                print_info(f"Credentials saved. Device set as default.")
            else:
                print_error("Pairing failed. Try again.")
        except Exception as e:
            print_error(f"Pairing error: {e}")
        finally:
            await pairing.close()

    asyncio.run(_run())


@cli.command()
@click.option("--protocol", "-p", type=click.Choice(list(PROTOCOL_MAP.keys())),
              help="Remove credentials for specific protocol.")
@click.option("--id", "identifier", help="Device identifier.")
@click.option("--all", "remove_all", is_flag=True, help="Remove device entirely.")
def unpair(protocol, identifier, remove_all):
    """🔓 Remove pairing with an Apple TV."""
    config = load_config()
    device = get_device(config, identifier)
    if not device:
        print_error("No device found. Specify with --id or set a default first.")
        return

    device_id = device.get("identifier", identifier)

    if remove_all:
        remove_device(config, device_id)
        save_config(config)
        print_success(f"Removed device {device.get('name', device_id)}")
    elif protocol:
        creds = device.get("credentials", {})
        if protocol in creds:
            del creds[protocol]
            save_config(config)
            print_success(f"Removed {protocol} credentials for {device.get('name', device_id)}")
        else:
            print_warning(f"No {protocol} credentials found for this device.")
    else:
        print_error("Specify --protocol or --all to unpair.")


@cli.command("default")
@click.argument("identifier", required=False)
def default_device(identifier):
    """⭐ Set or show the default Apple TV device."""
    config = load_config()
    if identifier:
        device = config.get("devices", {}).get(identifier)
        if not device:
            # Try matching by name
            for dev_id, dev in config.get("devices", {}).items():
                if dev.get("name", "").lower() == identifier.lower():
                    identifier = dev_id
                    device = dev
                    break
        if not device:
            print_error(f"Device '{identifier}' not found. Run 'atv scan' and 'atv pair' first.")
            return
        set_default(config, identifier)
        save_config(config)
        print_success(f"Default device set to: {device.get('name', identifier)}")
    else:
        default_id = config.get("default_device")
        if default_id:
            device = config.get("devices", {}).get(default_id, {})
            print_panel("Default Device", {
                "Name": device.get("name", "Unknown"),
                "Address": device.get("address", "Unknown"),
                "Identifier": default_id,
                "Protocols": ", ".join(device.get("credentials", {}).keys()) or "None",
            }, "⭐")
        else:
            print_warning("No default device set. Use: atv default <identifier>")


@cli.command("devices")
def list_saved_devices():
    """📋 List all saved/paired devices."""
    config = load_config()
    devs = list_devices(config)
    if not devs:
        print_warning("No paired devices. Run 'atv scan' then 'atv pair'.")
        return

    default_id = config.get("default_device")

    if is_json_mode():
        for d in devs:
            if d.get("credentials"):
                d["credentials"] = {
                    proto: bool(cred) for proto, cred in d["credentials"].items()
                }
        print_json(devs)
        return

    from rich.table import Table
    from rich import box
    table = Table(title="📋 Paired Devices", box=box.ROUNDED, show_lines=True)
    table.add_column("", style="bold", width=3)
    table.add_column("Name", style="bold cyan")
    table.add_column("Address", style="yellow")
    table.add_column("Identifier", style="dim")
    table.add_column("Protocols", style="green")

    for d in devs:
        is_default = "⭐" if d.get("identifier") == default_id else ""
        creds = d.get("credentials", {})
        if creds:
            protocols = ", ".join(f"{p} ✓" for p in creds.keys())
        else:
            protocols = "—"
        table.add_row(is_default, d.get("name", "?"), d.get("address", "?"),
                       d.get("identifier", "?"), protocols)
    console.print(table)


@cli.command("status", hidden=True)
def status_cmd():
    """Show quick status overview."""
    config = load_config()
    devs = list_devices(config)
    default_id = config.get("default_device")

    if not devs:
        console.print("[dim]No paired devices. Get started:[/]")
        console.print("  [bold]atv scan[/]   → Discover Apple TVs")
        console.print("  [bold]atv pair[/]   → Pair with a device")
        console.print("  [bold]atv --help[/] → See all commands")
        return

    default_dev = config.get("devices", {}).get(default_id, {}) if default_id else {}
    console.print(f"[bold]Default:[/] {default_dev.get('name', 'None')} ({default_dev.get('address', '?')})")
    console.print(f"[bold]Paired:[/]  {len(devs)} device(s)")
    protocols = list(default_dev.get("credentials", {}).keys())
    console.print(f"[bold]Protocols:[/] {', '.join(protocols) if protocols else 'none'}")
    console.print()
    console.print("[dim]Use [bold]atv --help[/bold] for all commands.[/dim]")


# ─── Add / Remove device commands ─────────────────────────────────


@click.command("add-device")
@click.option("--host", default=None, help="IP address of the Apple TV to add.")
def add_cmd(host):
    """Add an Apple TV: scan, pair all protocols, set as default."""
    async def _run():
        # 1. Scan for devices
        print_info("Scanning for Apple TVs (timeout: 5s)...")
        scan_kwargs = {"timeout": 5}
        if host:
            scan_kwargs["hosts"] = [host]
        devices = await pyatv.scan(asyncio.get_event_loop(), **scan_kwargs)

        if not devices:
            print_error("No Apple TVs found. Make sure your device is on the same network.")
            return

        # 2. Pick a device
        if len(devices) == 1 or host:
            device = devices[0]
        else:
            print_device_table(devices)
            console.print()
            for i, d in enumerate(devices, 1):
                console.print(f"  [bold]{i}[/]) {d.name} ({d.address})")
            console.print()
            choice = click.prompt("Select a device", type=int, default=1)
            if choice < 1 or choice > len(devices):
                print_error("Invalid selection.")
                return
            device = devices[choice - 1]

        print_info(f"Selected [bold]{device.name}[/] at {device.address}")

        # 3. Clear any existing device in config (single-device simplicity)
        config = load_config()
        existing_ids = list(config.get("devices", {}).keys())
        for eid in existing_ids:
            remove_device(config, eid)
        config["default_device"] = None

        # 4. Add the new device entry
        add_device(config, device.identifier, device.name, str(device.address))

        # 5. Pair with all available protocols (companion first, then airplay)
        paired_protocols = []
        for proto_name in ("companion", "airplay"):
            proto_enum = PROTOCOL_MAP[proto_name]
            # Check if device advertises this protocol
            if not any(s.protocol == proto_enum for s in device.services):
                print_warning(f"Protocol {proto_name} not available on this device, skipping.")
                continue

            print_info(f"Pairing via [bold]{proto_name}[/]...")
            try:
                pairing = await pyatv.pair(device, proto_enum, asyncio.get_event_loop())
                await pairing.begin()

                if pairing.device_provides_pin:
                    console.print(f"\n[bold yellow]Check your Apple TV — a PIN code should be displayed.[/]")
                    pin = click.prompt("Enter the 4-digit PIN", type=str)
                    pairing.pin(int(pin))
                elif not pairing.has_paired:
                    pin = click.prompt(f"Enter PIN for {proto_name} pairing", type=str)
                    pairing.pin(int(pin))

                await pairing.finish()

                if pairing.has_paired:
                    credentials = pairing.service.credentials
                    set_credentials(config, device.identifier, proto_name, credentials)
                    paired_protocols.append(proto_name)
                    print_success(f"Paired via {proto_name}")
                else:
                    print_warning(f"Pairing via {proto_name} did not complete, skipping.")
                await pairing.close()
            except Exception as e:
                print_warning(f"Failed to pair via {proto_name}: {e}")

        if not paired_protocols:
            print_error("Could not pair with any protocol. Device was not saved.")
            # Remove the device we just added since no protocols paired
            try:
                remove_device(config, device.identifier)
            except KeyError:
                pass
            save_config(config)
            return

        # 6. Set as default and save
        set_default(config, device.identifier)
        save_config(config)

        print_success(
            f"Added {device.name} as default device "
            f"(protocols: {', '.join(paired_protocols)})"
        )

    asyncio.run(_run())


@click.command("delete-device")
def remove_cmd():
    """Remove the saved Apple TV device."""
    config = load_config()
    default_id = config.get("default_device")

    if not default_id or default_id not in config.get("devices", {}):
        # Check if there are any devices at all
        devices = config.get("devices", {})
        if not devices:
            print_warning("No saved devices to remove.")
            return
        # Remove the first (only) device
        default_id = next(iter(devices))

    device = config["devices"][default_id]
    device_name = device.get("name", default_id)

    remove_device(config, default_id)
    config["default_device"] = None
    save_config(config)

    print_success(f"Removed device: {device_name}")


cli.add_command(add_cmd, "add")
cli.add_command(remove_cmd, "remove")


if __name__ == "__main__":
    cli()
