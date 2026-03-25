"""🎮 Remote control commands for Apple TV."""

from __future__ import annotations

import click
from pyatv.const import ShuffleState, RepeatState

from pyatv_cli.connection import connect_device, run_async, device_options
from pyatv_cli.output import print_success, print_error


@click.group()
def remote():
    """🎮 Remote control commands."""


def _remote_cmd(method_name: str, description: str) -> click.Command:
    """Factory for simple remote control commands."""

    @click.command(name=method_name.replace("_", "-"), help=description)
    @device_options
    def cmd(device, host):
        async def _run():
            atv = await connect_device(device, host)
            try:
                method = getattr(atv.remote_control, method_name)
                await method()
                print_success(f"Sent: {method_name.replace('_', ' ').title()}")
            except Exception as e:
                print_error(f"Failed: {e}")
            finally:
                atv.close()

        run_async(_run())

    return cmd


# Navigation
remote.add_command(_remote_cmd("up", "Navigate up"))
remote.add_command(_remote_cmd("down", "Navigate down"))
remote.add_command(_remote_cmd("left", "Navigate left"))
remote.add_command(_remote_cmd("right", "Navigate right"))
remote.add_command(_remote_cmd("select", "Select/confirm"))
remote.add_command(_remote_cmd("menu", "Menu/back button"))

# Playback
remote.add_command(_remote_cmd("play", "Play"))
remote.add_command(_remote_cmd("play_pause", "Toggle play/pause"))
remote.add_command(_remote_cmd("pause", "Pause"))
remote.add_command(_remote_cmd("stop", "Stop"))
remote.add_command(_remote_cmd("next", "Next track"))
remote.add_command(_remote_cmd("previous", "Previous track"))
remote.add_command(_remote_cmd("skip_forward", "Skip forward"))
remote.add_command(_remote_cmd("skip_backward", "Skip backward"))

# Volume
remote.add_command(_remote_cmd("volume_up", "Volume up"))
remote.add_command(_remote_cmd("volume_down", "Volume down"))

# System
remote.add_command(_remote_cmd("home", "Home button"))
remote.add_command(_remote_cmd("home_hold", "Long press home"))
remote.add_command(_remote_cmd("top_menu", "Top menu"))
remote.add_command(_remote_cmd("screensaver", "Activate screensaver"))
remote.add_command(_remote_cmd("guide", "Open guide"))
remote.add_command(_remote_cmd("control_center", "Open control center"))

# Channel
remote.add_command(_remote_cmd("channel_up", "Channel up"))
remote.add_command(_remote_cmd("channel_down", "Channel down"))


# --- Special commands with arguments ---

_SHUFFLE_MAP = {
    "off": ShuffleState.Off,
    "songs": ShuffleState.Songs,
    "albums": ShuffleState.Albums,
}

_REPEAT_MAP = {
    "off": RepeatState.Off,
    "track": RepeatState.Track,
    "all": RepeatState.All,
}


@remote.command(name="set-position")
@click.argument("seconds", type=float)
@device_options
def set_position(seconds, device, host):
    """Set playback position (seconds)."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            await atv.remote_control.set_position(seconds)
            print_success(f"Position set to {seconds}s")
        except Exception as e:
            print_error(f"Failed to set position: {e}")
        finally:
            atv.close()

    run_async(_run())


@remote.command(name="set-shuffle")
@click.argument("state", type=click.Choice(["off", "songs", "albums"]))
@device_options
def set_shuffle(state, device, host):
    """Set shuffle mode (off, songs, albums)."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            await atv.remote_control.set_shuffle(_SHUFFLE_MAP[state])
            print_success(f"Shuffle set to {state}")
        except Exception as e:
            print_error(f"Failed to set shuffle: {e}")
        finally:
            atv.close()

    run_async(_run())


@remote.command(name="set-repeat")
@click.argument("state", type=click.Choice(["off", "track", "all"]))
@device_options
def set_repeat(state, device, host):
    """Set repeat mode (off, track, all)."""

    async def _run():
        atv = await connect_device(device, host)
        try:
            await atv.remote_control.set_repeat(_REPEAT_MAP[state])
            print_success(f"Repeat set to {state}")
        except Exception as e:
            print_error(f"Failed to set repeat: {e}")
        finally:
            atv.close()

    run_async(_run())
