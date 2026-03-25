"""Rich output helpers for pyatv-cli.

Provides formatted console output with optional JSON mode
for scripting and automation.
"""

from __future__ import annotations

import json
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
error_console = Console(stderr=True)

_json_mode: bool = False


def set_json_mode(enabled: bool) -> None:
    """Enable or disable JSON output mode."""
    global _json_mode
    _json_mode = enabled


def is_json_mode() -> bool:
    """Return whether JSON output mode is active."""
    return _json_mode


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    console.print_json(json.dumps(data, default=str))


def print_success(message: str) -> None:
    """Print a success message."""
    if _json_mode:
        print_json({"status": "success", "message": message})
    else:
        console.print(f"[bold green]✓[/] {message}")


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    if _json_mode:
        print_json({"status": "error", "message": message})
    else:
        error_console.print(f"[bold red]✗[/] {message}")


def print_warning(message: str) -> None:
    """Print a warning message (suppressed in JSON mode)."""
    if _json_mode:
        return
    console.print(f"[bold yellow]⚠[/] {message}")


def print_info(message: str) -> None:
    """Print an informational message (suppressed in JSON mode)."""
    if _json_mode:
        return
    console.print(f"[bold blue]ℹ[/] {message}")


def print_device_table(devices: list[Any]) -> None:
    """Print a rich table of discovered Apple TV devices."""
    if _json_mode:
        print_json([
            {
                "name": d.name,
                "model": getattr(d.device_info, "model_str", None) or "Unknown",
                "address": str(d.address),
                "identifier": d.identifier,
                "os": getattr(d.device_info.operating_system, "name", "Unknown"),
                "version": d.device_info.version or "",
            }
            for d in devices
        ])
        return

    table = Table(title="🍎 Apple TV Devices", box=box.ROUNDED, show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Model", style="green")
    table.add_column("Address", style="yellow")
    table.add_column("Identifier", style="dim")
    table.add_column("OS", style="magenta")

    for d in devices:
        os_name = getattr(d.device_info.operating_system, "name", "Unknown")
        version = d.device_info.version or ""
        table.add_row(
            d.name,
            getattr(d.device_info, "model_str", None) or "Unknown",
            str(d.address),
            d.identifier,
            f"{os_name} {version}".strip(),
        )

    console.print(table)


def print_panel(title: str, data: dict[str, Any], emoji: str = "📺") -> None:
    """Print a rich panel with key-value data."""
    if _json_mode:
        print_json(data)
        return

    lines = [f"[bold]{k}:[/] {v}" for k, v in data.items()]
    console.print(Panel(
        "\n".join(lines),
        title=f"{emoji} {title}",
        box=box.ROUNDED,
        border_style="cyan",
    ))


def print_kv(key: str, value: Any, emoji: str = "") -> None:
    """Print a single key-value pair."""
    if _json_mode:
        print_json({key: value})
    else:
        prefix = f"{emoji} " if emoji else ""
        console.print(f"{prefix}[bold]{key}:[/] {value}")


def make_table(title: str, columns: list[tuple[str, str]]) -> Table:
    """Create a Rich table with predefined columns.

    Args:
        title: Table title.
        columns: List of (column_name, style) tuples.

    Returns:
        A Table instance ready for add_row() calls.
    """
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    for name, style in columns:
        table.add_column(name, style=style)
    return table
