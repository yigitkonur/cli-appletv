"""🎵 Now playing info and artwork commands."""

from __future__ import annotations

import click

from pyatv_cli.connection import connect_device, run_async, device_options
from pyatv_cli.output import (
    print_panel,
    print_success,
    print_error,
    print_json,
    is_json_mode,
    console,
)


def _fmt_time(seconds) -> str:
    """Format seconds into human-readable time string."""
    if seconds is None:
        return "—"
    total = int(seconds)
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


@click.group()
def media():
    """🎵 Now playing info and artwork."""


@media.command()
@device_options
def info(device, host):
    """Show what's currently playing."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            playing = await atv.metadata.playing()
            data = {
                "Title": playing.title or "—",
                "Artist": playing.artist or "—",
                "Album": playing.album or "—",
                "Genre": playing.genre or "—",
                "Media Type": str(playing.media_type),
                "State": str(playing.device_state),
                "Position": f"{_fmt_time(playing.position)} / {_fmt_time(playing.total_time)}",
                "Shuffle": str(playing.shuffle) if playing.shuffle else "—",
                "Repeat": str(playing.repeat) if playing.repeat else "—",
            }

            # App info
            app = getattr(playing, "app", None)
            if app:
                data["App"] = f"{app.name} ({app.identifier})"

            # Series / episode info
            if playing.series_name:
                data["Series"] = playing.series_name
            if playing.season_number is not None:
                data["Season"] = str(playing.season_number)
            if playing.episode_number is not None:
                data["Episode"] = str(playing.episode_number)

            if is_json_mode():
                print_json(data)
            else:
                print_panel("Now Playing", data, "🎵")
        except Exception as e:
            print_error(f"Failed to get now-playing info: {e}")
        finally:
            atv.close()

    run_async(_run())


@media.command()
@click.option("--output", "-o", default="artwork.png", help="Output file path")
@click.option("--width", "-w", type=int, default=512, help="Artwork width")
@click.option("--height", type=int, default=512, help="Artwork height")
@device_options
def artwork(output, width, height, device, host):
    """Download current artwork."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            art = await atv.metadata.artwork(width=width, height=height)
            if art and art.bytes:
                with open(output, "wb") as f:
                    f.write(art.bytes)
                print_success(
                    f"Artwork saved to {output} ({len(art.bytes)} bytes, {art.mimetype})"
                )
            else:
                print_error("No artwork available")
        except Exception as e:
            print_error(f"Failed to download artwork: {e}")
        finally:
            atv.close()

    run_async(_run())
