"""Touch gesture commands for pyatv-cli."""

from __future__ import annotations

import asyncio

import click

from pyatv_cli.connection import connect_device, device_options, run_async
from pyatv_cli.output import print_error, print_success, is_json_mode, print_json


@click.group()
def touch():
    """👆 Touch gestures."""
    pass


@touch.command()
@click.argument("direction", type=click.Choice(["up", "down", "left", "right"]))
@click.option("--duration", "-D", type=int, default=300, help="Duration in ms.")
@device_options
def swipe(direction: str, duration: int, device: str | None, host: str | None) -> None:
    """Swipe in a direction."""
    coords = {
        "up": (500, 800, 500, 200),
        "down": (500, 200, 500, 800),
        "left": (800, 500, 200, 500),
        "right": (200, 500, 800, 500),
    }
    start_x, start_y, end_x, end_y = coords[direction]

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.touch.swipe(start_x, start_y, end_x, end_y, duration)
            print_success(f"Swiped {direction}")
        except Exception as exc:
            print_error(f"Swipe failed: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())


@touch.command(name="swipe-custom")
@click.argument("start_x", type=int)
@click.argument("start_y", type=int)
@click.argument("end_x", type=int)
@click.argument("end_y", type=int)
@click.option("--duration", "-D", type=int, default=300, help="Duration in ms.")
@device_options
def swipe_custom(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: int,
    device: str | None,
    host: str | None,
) -> None:
    """Custom swipe with coordinates (0-1000 range)."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.touch.swipe(start_x, start_y, end_x, end_y, duration)
            print_success(f"Swiped ({start_x},{start_y}) → ({end_x},{end_y})")
        except Exception as exc:
            print_error(f"Custom swipe failed: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())


@touch.command()
@click.option("--x", type=int, default=500, help="X coordinate (0-1000).")
@click.option("--y", type=int, default=500, help="Y coordinate (0-1000).")
@device_options
def tap(x: int, y: int, device: str | None, host: str | None) -> None:
    """Single tap at position."""
    from pyatv.const import InputAction

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.touch.click(InputAction.SingleTap)
            print_success(f"Tapped at ({x},{y})")
        except Exception as exc:
            print_error(f"Tap failed: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())


@touch.command(name="double-tap")
@click.option("--x", type=int, default=500, help="X coordinate (0-1000).")
@click.option("--y", type=int, default=500, help="Y coordinate (0-1000).")
@device_options
def double_tap(x: int, y: int, device: str | None, host: str | None) -> None:
    """Double tap at position."""
    from pyatv.const import InputAction

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.touch.click(InputAction.DoubleTap)
            print_success(f"Double-tapped at ({x},{y})")
        except Exception as exc:
            print_error(f"Double tap failed: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())


@touch.command()
@click.option("--x", type=int, default=500, help="X coordinate (0-1000).")
@click.option("--y", type=int, default=500, help="Y coordinate (0-1000).")
@click.option("--duration", "-D", type=float, default=1.0, help="Hold duration in seconds.")
@device_options
def hold(x: int, y: int, duration: float, device: str | None, host: str | None) -> None:
    """Long press/hold at position."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            # Hold = begin touch, wait, then end
            await atv.touch.swipe(x, y, x, y, int(duration * 1000))
            print_success(f"Held at ({x},{y}) for {duration}s")
        except Exception as exc:
            print_error(f"Hold failed: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())
