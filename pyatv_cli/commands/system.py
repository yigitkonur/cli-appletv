"""System information commands for pyatv-cli."""

from __future__ import annotations

import click

from pyatv_cli.config import load_config, get_device
from pyatv_cli.connection import connect_device, device_options, run_async
from pyatv_cli.output import (
    console,
    is_json_mode,
    make_table,
    print_error,
    print_json,
)

from rich import box
from rich.panel import Panel


@click.group()
def system():
    """🖥️  System information."""
    pass


@system.command()
@device_options
def info(device: str | None, host: str | None) -> None:
    """Show device information."""

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            di = atv.device_info

            # Get the device name from the config object
            config_data = load_config()
            dev_conf = get_device(config_data, device)
            name = dev_conf.get("name", str(di.model)) if dev_conf else str(di.model)
            model = getattr(di, "model_str", None) or str(di.model)
            os_name = getattr(di.operating_system, "name", "Unknown")
            version = di.version or "Unknown"
            build = di.build_number or "Unknown"
            mac = di.mac or "Unknown"

            # Collect service info from stored config
            services: list[dict[str, str]] = []
            stored_creds = dev_conf.get("credentials", {}) if dev_conf else {}
            if hasattr(atv, "_config"):
                for svc in atv._config.services:
                    proto = svc.protocol.name.lower()
                    paired = "✅ Paired" if proto in stored_creds else "⚠️  Not paired"
                    services.append({"protocol": svc.protocol.name, "status": paired})

            if is_json_mode():
                print_json({
                    "name": name,
                    "model": model,
                    "os": os_name,
                    "version": version,
                    "build": build,
                    "mac": mac,
                    "services": [
                        {"protocol": s["protocol"], "paired": "credentials" not in s.get("status", "") or "Paired" in s["status"]}
                        for s in services
                    ],
                })
                return

            lines: list[str] = [
                f"[bold]Model:[/]       {model}",
                f"[bold]OS:[/]          {os_name} {version}",
                f"[bold]Build:[/]       {build}",
                f"[bold]MAC:[/]         {mac}",
            ]

            if services:
                lines.append("")
                lines.append("[bold]Services:[/]")
                for svc in services:
                    lines.append(f"  {svc['protocol']:12s} {svc['status']}")

            console.print(Panel(
                "\n".join(lines),
                title=f"📺 {name}",
                box=box.ROUNDED,
                border_style="cyan",
            ))
        except Exception as exc:
            print_error(f"Failed to get device info: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())


@system.command()
@device_options
def features(device: str | None, host: str | None) -> None:
    """List all supported features."""
    from pyatv.const import FeatureName, FeatureState

    async def _run() -> None:
        atv = await connect_device(device, host)
        try:
            all_features = atv.features.all_features()

            if is_json_mode():
                data = [
                    {
                        "feature": feat.name,
                        "state": (info.state.name if hasattr(info, "state") else str(info)),
                    }
                    for feat, info in sorted(
                        all_features.items(), key=lambda kv: kv[0].name
                    )
                ]
                print_json(data)
                return

            state_display = {
                FeatureState.Available: "[green]🟢 Available[/]",
                FeatureState.Unavailable: "[yellow]🟡 Unavailable[/]",
                FeatureState.Unsupported: "[red]🔴 Unsupported[/]",
                FeatureState.Unknown: "[dim]⚪ Unknown[/]",
            }

            table = make_table(
                "🎛️  Features",
                [("Feature", "bold cyan"), ("State", "")],
            )

            for feat, info in sorted(
                all_features.items(), key=lambda kv: kv[0].name
            ):
                state = info.state if hasattr(info, "state") else info
                label = state_display.get(state, f"[dim]{state}[/]")
                table.add_row(feat.name, label)

            console.print(table)
        except Exception as exc:
            print_error(f"Failed to list features: {exc}")
            raise SystemExit(1)
        finally:
            atv.close()

    run_async(_run())
