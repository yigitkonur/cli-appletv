"""Async connection helpers for pyatv-cli.

Provides device scanning, connection with stored credentials,
and Click decorator for common device options.
"""

from __future__ import annotations

import asyncio
import functools
import sys
from typing import Any, Callable, TypeVar

import click
import pyatv
from pyatv.const import Protocol

from pyatv_cli.config import load_config, get_device
from pyatv_cli.output import print_error

F = TypeVar("F", bound=Callable[..., Any])

PROTOCOL_MAP: dict[str, Protocol] = {
    "companion": Protocol.Companion,
    "airplay": Protocol.AirPlay,
    "mrp": Protocol.MRP,
    "dmap": Protocol.DMAP,
    "raop": Protocol.RAOP,
}


async def find_device(
    identifier: str | None = None,
    host: str | None = None,
) -> Any | None:
    """Scan the network and find a specific Apple TV.

    Uses stored config to narrow the scan when possible.
    """
    config = load_config()
    device_conf = get_device(config, identifier)

    scan_kwargs: dict[str, Any] = {}
    if device_conf:
        scan_kwargs["identifier"] = device_conf["identifier"]
    if host:
        scan_kwargs["hosts"] = [host]

    try:
        devices = await pyatv.scan(asyncio.get_event_loop(), timeout=5, **scan_kwargs)
    except (ValueError, OSError) as exc:
        print_error(f"Invalid host address: {host or identifier}")
        sys.exit(1)

    if not devices:
        return None
    return devices[0]


def _find_device_config(config: dict, scanned_id: str, host: str | None = None) -> dict | None:
    """Match a scanned device to stored config.

    pyatv may return different identifier formats (MAC vs UUID) across scans,
    so we try: exact match, then normalized substring match, then address match.
    """
    devices = config.get("devices", {})

    # 1. Exact match
    if scanned_id in devices:
        return devices[scanned_id]

    # 2. Normalize both sides (strip colons/hyphens, uppercase) and compare
    norm = scanned_id.replace(":", "").replace("-", "").upper()
    for dev_id, dev in devices.items():
        stored_norm = dev_id.replace(":", "").replace("-", "").upper()
        if norm == stored_norm or norm in stored_norm or stored_norm in norm:
            return dev

    # 3. Match by host/address
    if host:
        for dev in devices.values():
            if dev.get("address") == host:
                return dev

    # 4. Fall back to default device
    default_id = config.get("default_device")
    if default_id and default_id in devices:
        return devices[default_id]

    return None


async def connect_device(
    identifier: str | None = None,
    host: str | None = None,
) -> Any:
    """Connect to an Apple TV using stored credentials.

    Raises ConnectionError if the device cannot be found.
    """
    conf = await find_device(identifier, host)
    if not conf:
        raise ConnectionError("Device not found. Run 'atv scan' first.")

    config = load_config()
    device_conf = _find_device_config(config, conf.identifier, host)

    if device_conf and "credentials" in device_conf:
        for proto_name, creds in device_conf["credentials"].items():
            if proto_name in PROTOCOL_MAP:
                conf.set_credentials(PROTOCOL_MAP[proto_name], creds)

    return await pyatv.connect(conf, asyncio.get_event_loop())


def run_async(coro: Any) -> Any:
    """Run an async coroutine from a synchronous Click command."""
    return asyncio.run(coro)


def device_options(f: F) -> F:
    """Click decorator that adds --device and --host options to a command."""

    @click.option(
        "--device", "-d",
        default=None,
        help="Device identifier (uses default device if omitted).",
    )
    @click.option(
        "--host", "-h",
        default=None,
        help="Device IP address or hostname.",
    )
    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return f(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
