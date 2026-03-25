"""⌨️  Virtual keyboard control commands."""

from __future__ import annotations

import click

from pyatv_cli.connection import connect_device, device_options, run_async
from pyatv_cli.output import (
    console,
    is_json_mode,
    print_error,
    print_json,
    print_kv,
    print_success,
)


@click.group()
def keyboard():
    """⌨️  Virtual keyboard control."""
    pass


@keyboard.command()
@device_options
def status(device: str | None, host: str | None) -> None:
    """Show keyboard focus state."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            state = atv.keyboard.text_focus_state

            if is_json_mode():
                print_json({"focus_state": str(state)})
                return

            print_kv("Focus State", state, emoji="⌨️")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@keyboard.command(name="get")
@device_options
def get_text(device: str | None, host: str | None) -> None:
    """Get current keyboard text."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            text = await atv.keyboard.text_get()

            if is_json_mode():
                print_json({"text": text})
                return

            if text:
                print_kv("Text", text, emoji="⌨️")
            else:
                console.print("[dim]No text in keyboard.[/dim]")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@keyboard.command(name="set")
@click.argument("text")
@device_options
def set_text(text: str, device: str | None, host: str | None) -> None:
    """Set keyboard text (replaces all)."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.keyboard.text_set(text)
            print_success(f"Keyboard text set to: {text}")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@keyboard.command()
@click.argument("text")
@device_options
def append(text: str, device: str | None, host: str | None) -> None:
    """Append text to keyboard."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.keyboard.text_append(text)
            print_success(f"Appended: {text}")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)


@keyboard.command()
@device_options
def clear(device: str | None, host: str | None) -> None:
    """Clear keyboard text."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.keyboard.text_clear()
            print_success("Keyboard text cleared")
        finally:
            atv.close()

    try:
        run_async(_run())
    except Exception as exc:
        print_error(str(exc))
        raise SystemExit(1)
