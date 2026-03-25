"""Configuration management for pyatv-cli.

Stores device info and credentials at ~/.config/pyatv-cli/config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR: Path = Path("~/.config/pyatv-cli").expanduser()
CONFIG_FILE: Path = CONFIG_DIR / "config.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "default_device": None,
    "devices": {},
}


def load_config() -> dict[str, Any]:
    """Load config from disk, or return empty default if missing/corrupt."""
    if not CONFIG_FILE.exists():
        return json.loads(json.dumps(_DEFAULT_CONFIG))  # deep copy
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure required top-level keys exist
        for key, default in _DEFAULT_CONFIG.items():
            data.setdefault(key, default if default is None else type(default)())
        return data
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(_DEFAULT_CONFIG))


def save_config(config: dict[str, Any]) -> None:
    """Write config to disk, creating the directory if needed."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_device(config: dict[str, Any], identifier: str | None = None) -> dict[str, Any] | None:
    """Get a device by identifier, or the default device if none specified."""
    devices = config.get("devices", {})
    if identifier:
        return devices.get(identifier)
    default_id = config.get("default_device")
    if default_id:
        return devices.get(default_id)
    return None


def add_device(
    config: dict[str, Any],
    identifier: str,
    name: str,
    address: str,
) -> dict[str, Any]:
    """Add or update a device entry. Returns the device dict."""
    devices = config.setdefault("devices", {})
    if identifier in devices:
        devices[identifier]["name"] = name
        devices[identifier]["address"] = address
    else:
        devices[identifier] = {
            "name": name,
            "address": address,
            "identifier": identifier,
            "credentials": {},
        }
    # Auto-set as default if it's the only device
    if len(devices) == 1:
        config["default_device"] = identifier
    return devices[identifier]


def set_credentials(
    config: dict[str, Any],
    identifier: str,
    protocol: str,
    credentials: str,
) -> None:
    """Store credentials for a device + protocol."""
    device = config.get("devices", {}).get(identifier)
    if device is None:
        raise KeyError(f"Device '{identifier}' not found in config")
    device.setdefault("credentials", {})[protocol] = credentials


def set_default(config: dict[str, Any], identifier: str) -> None:
    """Set the default device."""
    if identifier not in config.get("devices", {}):
        raise KeyError(f"Device '{identifier}' not found in config")
    config["default_device"] = identifier


def remove_device(config: dict[str, Any], identifier: str) -> None:
    """Remove a device from config."""
    devices = config.get("devices", {})
    if identifier not in devices:
        raise KeyError(f"Device '{identifier}' not found in config")
    del devices[identifier]
    if config.get("default_device") == identifier:
        config["default_device"] = next(iter(devices), None)


def list_devices(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of all stored devices with their identifiers."""
    result = []
    default_id = config.get("default_device")
    for dev_id, dev in config.get("devices", {}).items():
        entry = {**dev, "identifier": dev_id, "is_default": dev_id == default_id}
        result.append(entry)
    return result
