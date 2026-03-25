"""Streaming commands for pyatv-cli."""

from __future__ import annotations

import click

from pyatv_cli.connection import connect_device, device_options, run_async
from pyatv_cli.output import print_error, print_success


@click.group()
def stream():
    """📡 Stream content to Apple TV."""
    pass


@stream.command()
@click.argument("url")
@device_options
def url(url: str, device: str | None, host: str | None) -> None:
    """Stream from a URL."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            await atv.stream.play_url(url)
            print_success(f"Streaming: {url}")
        except Exception as exc:
            print_error(f"Stream failed: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())


@stream.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--title", "-t", default=None, help="Media title.")
@click.option("--artist", "-a", default=None, help="Artist name.")
@click.option("--album", default=None, help="Album name.")
@device_options
def file(
    path: str,
    title: str | None,
    artist: str | None,
    album: str | None,
    device: str | None,
    host: str | None,
) -> None:
    """Stream a local file."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            metadata: dict[str, str] = {}
            if title:
                metadata["title"] = title
            if artist:
                metadata["artist"] = artist
            if album:
                metadata["album"] = album

            kwargs = {"metadata": metadata} if metadata else {}
            await atv.stream.stream_file(path, **kwargs)
            print_success(f"Streaming: {path}")
        except Exception as exc:
            print_error(f"File stream failed: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())
