"""⚡ Power control commands for Apple TV."""

from __future__ import annotations

import click

from pyatv_cli.connection import connect_device, run_async, device_options
from pyatv_cli.output import print_success, print_error, print_kv, print_json, is_json_mode


@click.group()
def power():
    """⚡ Power control for Apple TV."""


@power.command()
@device_options
def status(device, host):
    """Show current power state."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            state = atv.power.power_state
            if is_json_mode():
                print_json({"power_state": str(state)})
            else:
                emoji = "🟢" if "On" in str(state) else "🔴"
                print_kv("Power State", f"{emoji} {state}")
        except Exception as e:
            print_error(f"Failed to get power state: {e}")
        finally:
            atv.close()

    run_async(_run())


@power.command(name="on")
@device_options
def turn_on(device, host):
    """Turn Apple TV on."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            await atv.power.turn_on()
            print_success("Apple TV turned ON 🟢")
        except Exception as e:
            print_error(f"Failed to turn on: {e}")
        finally:
            atv.close()

    run_async(_run())


@power.command(name="off")
@device_options
def turn_off(device, host):
    """Turn Apple TV off."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            await atv.power.turn_off()
            print_success("Apple TV turned OFF 🔴")
        except Exception as e:
            print_error(f"Failed to turn off: {e}")
        finally:
            atv.close()

    run_async(_run())


@power.command()
@device_options
def toggle(device, host):
    """Toggle power state."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            state = str(atv.power.power_state)
            if "On" in state:
                await atv.power.turn_off()
                print_success("Apple TV turned OFF 🔴")
            else:
                await atv.power.turn_on()
                print_success("Apple TV turned ON 🟢")
        except Exception as e:
            print_error(f"Failed to toggle power: {e}")
        finally:
            atv.close()

    run_async(_run())
