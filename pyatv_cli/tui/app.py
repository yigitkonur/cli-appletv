"""Apple TV TUI v5 — Polished single-column remote."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Footer, Header, Label, ListItem, ListView,
    ProgressBar, Static, RichLog, Rule, OptionList,
)
from textual.widgets.option_list import Option
from textual.message import Message
from textual import work

from pyatv_cli.config import load_config, get_device, list_devices
from pyatv_cli.connection import connect_device, find_device

try:
    from pyatv.interface import PushListener as _PushListenerBase
except ImportError:
    _PushListenerBase = object  # type: ignore[misc,assignment]

try:
    from pyatv.const import FeatureName, FeatureState, PowerState
except ImportError:
    FeatureName = FeatureState = PowerState = None  # type: ignore


def fmt_time(seconds: float | int | None) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ─── Feature probing ─────────────────────────────────────────────

class DeviceCaps:
    def __init__(self):
        self.has_set_volume = False
        self.has_volume_up = False
        self.has_volume_down = False
        self.has_volume_read = False
        self.has_title = False
        self.has_push = False
        self.has_app = False
        self.has_shuffle = False
        self.has_repeat = False
        self._available: set[str] = set()
        self.vol_step = 5.0

    @classmethod
    def from_atv(cls, atv: Any) -> "DeviceCaps":
        caps = cls()
        if not FeatureName or not FeatureState:
            return caps
        try:
            features = atv.features
            def _ok(name) -> bool:
                try:
                    return features.get_feature(name).state == FeatureState.Available
                except Exception:
                    return False
            caps.has_set_volume = _ok(FeatureName.SetVolume)
            caps.has_volume_up = _ok(FeatureName.VolumeUp)
            caps.has_volume_down = _ok(FeatureName.VolumeDown)
            caps.has_volume_read = _ok(FeatureName.Volume)
            caps.has_title = _ok(FeatureName.Title)
            caps.has_push = _ok(FeatureName.PushUpdates)
            caps.has_shuffle = _ok(FeatureName.SetShuffle)
            caps.has_repeat = _ok(FeatureName.SetRepeat)
            try:
                caps.has_app = _ok(FeatureName.App)
            except Exception:
                pass
            for fn in FeatureName:
                if _ok(fn):
                    caps._available.add(fn.name)
        except Exception:
            pass
        return caps

    @property
    def vol_method(self) -> str:
        if self.has_set_volume:
            return "absolute"
        if self.has_volume_up or self.has_volume_down:
            return "relative"
        return "none"

    def is_available(self, name: str) -> bool:
        return name in self._available


# ─── Device Selector ──────────────────────────────────────────────

class DeviceSelectScreen(ModalScreen[str | None]):
    DEFAULT_CSS = """
    DeviceSelectScreen { align: center middle; }
    DeviceSelectScreen > #dlg {
        width: 56; max-height: 70%; background: $surface;
        border: heavy $primary; padding: 2 3;
    }
    DeviceSelectScreen #dlg-title {
        text-align: center; text-style: bold; color: $primary;
        width: 100%; margin-bottom: 1;
    }
    DeviceSelectScreen OptionList { height: auto; max-height: 16; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel", priority=True)]

    def __init__(self, devices: list[dict]):
        super().__init__()
        self._devices = devices

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Label("Select Apple TV", id="dlg-title")
            options = []
            for d in self._devices:
                name = d.get("name", "Unknown")
                addr = d.get("address", "?")
                dflt = " [dim](default)[/]" if d.get("is_default") else ""
                options.append(Option(f"  {name}  [dim]{addr}[/]{dflt}"))
            yield OptionList(*options, id="device-list")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if 0 <= idx < len(self._devices):
            self.dismiss(self._devices[idx].get("identifier"))
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ─── Help Screen ─────────────────────────────────────────────────

class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("question_mark", "dismiss", "Close", priority=True),
    ]
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > #hdlg {
        width: 52; max-height: 85%; background: $surface;
        border: heavy $primary; padding: 1 2;
    }
    HelpScreen #htitle {
        text-align: center; text-style: bold; color: $primary;
        width: 100%; margin-bottom: 1;
    }
    HelpScreen .hsec { margin-bottom: 1; }
    HelpScreen .hhead { text-style: bold; color: $accent; }
    HelpScreen .hk { padding-left: 2; color: $text-muted; }
    HelpScreen #hfoot { text-align: center; margin-top: 1; color: $text-muted; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="hdlg"):
            yield Label("Keyboard Shortcuts", id="htitle")
            with Vertical(classes="hsec"):
                yield Label("[bold]Navigation[/]", classes="hhead")
                for l in ["Arrows/WASD  D-pad", "Enter/o      Select",
                          "Esc/BS/b     Back", "h            Home"]:
                    yield Label(l, classes="hk")
            with Vertical(classes="hsec"):
                yield Label("[bold]Playback[/]", classes="hhead")
                for l in ["Space        Play/pause", "s            Stop",
                          "n/>          Next", "p/<          Previous"]:
                    yield Label(l, classes="hk")
            with Vertical(classes="hsec"):
                yield Label("[bold]Volume[/]", classes="hhead")
                for l in ["+/=          Up", "-/_          Down", "0            Mute"]:
                    yield Label(l, classes="hk")
            with Vertical(classes="hsec"):
                yield Label("[bold]System[/]", classes="hhead")
                for l in ["P            Power", "r            Reconnect",
                          "t            Theme", "?            Help", "q            Quit"]:
                    yield Label(l, classes="hk")
            yield Label("[dim]Esc to close[/]", id="hfoot")


# ─── Now Playing (hidden when metadata unavailable) ───────────────

class NowPlaying(Static):
    DEFAULT_CSS = """
    NowPlaying { height: auto; padding: 0 2; }
    NowPlaying #np-title { width: 100%; text-style: bold; }
    NowPlaying #np-artist { width: 100%; color: $accent; }
    NowPlaying #np-state-row { height: 1; width: 100%; margin-top: 1; }
    NowPlaying #np-state { width: auto; }
    NowPlaying #np-extra { width: 1fr; text-align: right; color: $text-muted; }
    NowPlaying #np-bar-row { height: 1; width: 100%; }
    NowPlaying #np-bar { width: 1fr; }
    NowPlaying #np-time { width: auto; min-width: 14; text-align: right; color: $text-muted; }
    """

    title: reactive[str] = reactive("Nothing Playing")
    artist: reactive[str] = reactive("")
    state: reactive[str] = reactive("Idle")
    position: reactive[float] = reactive(0.0)
    duration: reactive[float] = reactive(0.0)
    app_name: reactive[str] = reactive("")
    shuffle: reactive[str] = reactive("")
    repeat: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Label("Nothing Playing", id="np-title")
        yield Label("", id="np-artist")
        with Horizontal(id="np-state-row"):
            yield Label("Idle", id="np-state")
            yield Label("", id="np-extra")
        with Horizontal(id="np-bar-row"):
            yield ProgressBar(total=100, show_eta=False, id="np-bar")
            yield Label("--:-- / --:--", id="np-time")

    def _u(self, sel: str, text: str) -> None:
        try:
            self.query_one(sel, Label).update(text)
        except Exception:
            pass

    def watch_title(self, v: str) -> None:
        self._u("#np-title", v or "Nothing Playing")
    def watch_artist(self, v: str) -> None:
        self._u("#np-artist", v or "")
    def watch_state(self, v: str) -> None:
        icons = {"Playing": "[green]>[/] Playing", "Paused": "[yellow]||[/] Paused",
                 "Idle": "[dim]Idle[/]", "Stopped": "[dim]Stopped[/]"}
        self._u("#np-state", icons.get(v, v))
    def watch_position(self, v: float) -> None:
        try:
            dur = self.duration or 1
            pct = min((v / dur) * 100, 100) if dur > 0 else 0
            self.query_one("#np-bar", ProgressBar).update(progress=pct)
            self.query_one("#np-time", Label).update(f"{fmt_time(v)} / {fmt_time(self.duration)}")
        except Exception:
            pass
    def watch_shuffle(self, v: str) -> None:
        self._update_extra()
    def watch_repeat(self, v: str) -> None:
        self._update_extra()
    def _update_extra(self) -> None:
        parts = []
        if self.shuffle and self.shuffle.lower() not in ("off", "false", "unknown", ""):
            parts.append("[cyan]Shuffle[/]")
        if self.repeat and self.repeat.lower() not in ("off", "false", "unknown", ""):
            parts.append(f"[magenta]Repeat: {self.repeat}[/]")
        self._u("#np-extra", "  ".join(parts))


# ─── Remote + Volume combined ─────────────────────────────────────

class RemotePanel(Static):
    """D-pad, playback controls, volume — all in one panel."""

    DEFAULT_CSS = """
    RemotePanel { height: auto; padding: 2 2 1 2; }
    RemotePanel .dpad-row { height: 3; align: center middle; width: 100%; }
    RemotePanel .dpad-row Button { width: 9; height: 3; margin: 0 0; }
    RemotePanel .dpad-spacer { width: 9; height: 3; }
    RemotePanel .ctrl-row { height: 3; margin-top: 1; align: center middle; }
    RemotePanel .ctrl-row Button { width: 9; height: 3; margin: 0 1; }
    RemotePanel .vol-row { height: 3; margin-top: 0; align: center middle; }
    RemotePanel .vol-row Button { width: 9; height: 3; margin: 0 1; }
    RemotePanel #vol-label { width: 100%; text-align: center; color: $text-muted; margin-top: 2; }
    """

    class RemoteCommand(Message):
        def __init__(self, command: str) -> None:
            self.command = command
            super().__init__()

    class PowerToggle(Message):
        pass

    class VolumeCommand(Message):
        def __init__(self, action: str) -> None:
            self.action = action
            super().__init__()

    def compose(self) -> ComposeResult:
        # D-pad
        with Horizontal(classes="dpad-row"):
            yield Static("", classes="dpad-spacer")
            yield Button("  \u25b2  ", id="btn-up", variant="primary")
            yield Static("", classes="dpad-spacer")
        with Horizontal(classes="dpad-row"):
            yield Button("  \u25c4  ", id="btn-left", variant="primary")
            yield Button(" OK ", id="btn-select", variant="success")
            yield Button("  \u25ba  ", id="btn-right", variant="primary")
        with Horizontal(classes="dpad-row"):
            yield Static("", classes="dpad-spacer")
            yield Button("  \u25bc  ", id="btn-down", variant="primary")
            yield Static("", classes="dpad-spacer")

        # Playback
        with Horizontal(classes="ctrl-row"):
            yield Button(" Prev ", id="btn-prev")
            yield Button(" Play ", id="btn-play-pause", variant="warning")
            yield Button(" Next ", id="btn-next")
            yield Button(" Stop ", id="btn-stop", variant="error")

        # System
        with Horizontal(classes="ctrl-row"):
            yield Button(" Home ", id="btn-home")
            yield Button(" Menu ", id="btn-menu")
            yield Button("Power", id="btn-power", variant="error")

        # Volume
        yield Label("[bold]Volume[/]", id="vol-label")
        with Horizontal(classes="vol-row"):
            yield Button("  \u2013  ", id="vol-down", variant="primary")
            yield Button("  +  ", id="vol-up", variant="primary")
            yield Button(" Mute ", id="vol-mute", variant="error")

    BUTTON_MAP = {
        "btn-up": "up", "btn-down": "down", "btn-left": "left", "btn-right": "right",
        "btn-select": "select", "btn-play-pause": "play_pause",
        "btn-prev": "previous", "btn-next": "next", "btn-stop": "stop",
        "btn-home": "home", "btn-menu": "menu",
    }

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-power":
            self.post_message(self.PowerToggle())
        elif bid in ("vol-down", "vol-up", "vol-mute"):
            actions = {"vol-down": "down", "vol-up": "up", "vol-mute": "mute"}
            self.post_message(self.VolumeCommand(actions[bid]))
        else:
            cmd = self.BUTTON_MAP.get(bid, "")
            if cmd:
                self.post_message(self.RemoteCommand(cmd))


# ─── Apps Panel ───────────────────────────────────────────────────

class AppListView(ListView):
    """ListView that doesn't capture arrow keys — those go to Apple TV D-pad."""

    BINDINGS = []  # remove all default key bindings

    def _on_key(self, event) -> None:
        # Let arrow keys pass through to the app (D-pad)
        if event.key in ("up", "down", "left", "right", "enter"):
            event.prevent_default()
            event.stop()
            return
        super()._on_key(event)


class AppsPanel(Static):
    DEFAULT_CSS = """
    AppsPanel { height: 1fr; padding: 1 2; }
    AppsPanel .ap-title { text-style: bold; margin-bottom: 1; }
    AppsPanel AppListView { height: 1fr; min-height: 3; scrollbar-visibility: hidden; }
    """

    _APP_RANK: dict[str, int] = {
        "com.google.ios.youtube": 0, "com.apple.TVWatchList": 1,
        "com.netflix.Netflix": 2, "com.disney.disneyplus": 3,
        "com.amazon.aiv.AIVApp": 4, "com.spotify.client": 5,
        "com.apple.Fitness": 6, "com.apple.TVMusic": 7,
        "com.hbo.hbonow": 8, "com.apple.TVPhotos": 9,
        "tv.plex.player": 10, "com.apple.podcasts": 11,
    }

    class LaunchApp(Message):
        def __init__(self, bundle_id: str) -> None:
            self.bundle_id = bundle_id
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("Apps", classes="ap-title")
        yield AppListView(id="apps-list")

    def set_apps(self, apps: list) -> None:
        lv = self.query_one("#apps-list", AppListView)
        lv.clear()
        ranked = sorted(apps, key=lambda a: self._APP_RANK.get(a.identifier, 100))
        for app in ranked:
            item = ListItem(Label(f"  {app.name}"))
            item._app_id = app.identifier  # noqa: SLF001
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        bid = getattr(event.item, "_app_id", None)
        if bid:
            self.post_message(self.LaunchApp(bid))


# ─── System Info ──────────────────────────────────────────────────

class SystemInfo(Static):
    DEFAULT_CSS = """
    SystemInfo { height: auto; padding: 1 2; }
    SystemInfo .si-title { text-style: bold; margin-bottom: 1; }
    SystemInfo #sys-content { color: $text-muted; }
    """

    def compose(self) -> ComposeResult:
        yield Label("System", classes="si-title")
        yield Label("[dim]Connecting...[/]", id="sys-content")

    def set_info(self, info: dict) -> None:
        lines = [f"[bold]{k}:[/] {v}" for k, v in info.items()]
        try:
            self.query_one("#sys-content", Label).update("\n".join(lines))
        except Exception:
            pass


# ─── Activity Log ─────────────────────────────────────────────────

class ActivityLog(RichLog):
    max_lines = 200
    DEFAULT_CSS = "ActivityLog { height: 100%; min-height: 3; padding: 0 1; scrollbar-visibility: hidden; }"


# ─── Push Listener ────────────────────────────────────────────────

class PushListener(_PushListenerBase):
    def __init__(self, callback):
        self._cb = callback
    def playstatus_update(self, updater, playing):
        self._cb(playing)
    def playstatus_error(self, updater, exception):
        pass


_CMD_FEATURE_MAP: dict[str, str] = {
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "select": "Select", "menu": "Menu", "home": "Home",
    "play_pause": "PlayPause", "stop": "Stop",
    "next": "Next", "previous": "Previous",
    "skip_forward": "SkipForward", "skip_backward": "SkipBackward",
    "top_menu": "TopMenu", "volume_up": "VolumeUp", "volume_down": "VolumeDown",
}


# ─── Main App ─────────────────────────────────────────────────────

class AppleTVApp(App):
    TITLE = "Apple TV Remote"
    SUB_TITLE = "pyatv-cli"

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-columns: 3fr 2fr;
        grid-rows: auto 1fr auto;
        grid-gutter: 0;
        padding: 0;
    }

    #conn-bar {
        column-span: 2; height: 1; width: 100%;
        text-align: center; text-style: bold; padding: 0 2;
        background: $surface-darken-1; color: $text-muted;
    }
    #conn-bar.ok { background: $success-darken-3; color: $success-lighten-2; }
    #conn-bar.err { background: $error-darken-2; color: $error-lighten-2; }

    #col-left {
        column-span: 1; row-span: 1; height: 100%;
        border-right: tall $surface-lighten-1;
    }
    #col-right {
        column-span: 1; row-span: 1; height: 100%;
    }

    #bottom-bar {
        column-span: 2; row-span: 1;
        height: auto; max-height: 12;
        layout: horizontal;
        border-top: tall $surface-lighten-1;
    }
    #bottom-apps { width: 1fr; height: auto; max-height: 10; }
    #bottom-sys { width: 1fr; height: auto; max-height: 10; border-left: tall $surface-lighten-1; }
    #bottom-log { width: 1fr; height: auto; max-height: 10; border-left: tall $surface-lighten-1; }
    #log-title { text-style: bold; padding: 0 1; color: $text-muted; }
    """

    BINDINGS = [
        Binding("up", "remote('up')", "Up"),
        Binding("down", "remote('down')", "Down"),
        Binding("left", "remote('left')", "Left"),
        Binding("right", "remote('right')", "Right"),
        Binding("w", "remote('up')", "", show=False),
        Binding("a", "remote('left')", "", show=False),
        Binding("enter", "remote('select')", "OK", priority=True),
        Binding("o", "remote('select')", "", show=False),
        Binding("escape", "remote('menu')", "Back", priority=True),
        Binding("backspace", "remote('menu')", "", priority=True, show=False),
        Binding("delete", "remote('menu')", "", show=False),
        Binding("m", "remote('menu')", "", show=False),
        Binding("b", "remote('menu')", "", show=False),
        Binding("h", "remote('home')", "Home"),
        Binding("space", "remote('play_pause')", "Play/Pause"),
        Binding("s", "remote('stop')", "Stop"),
        Binding("n", "remote('next')", "Next"),
        Binding("p", "remote('previous')", "Prev"),
        Binding("period", "remote('skip_forward')", "Skip>"),
        Binding("comma", "remote('skip_backward')", "<Skip"),
        Binding("bracketright", "remote('skip_forward')", "", show=False),
        Binding("bracketleft", "remote('skip_backward')", "", show=False),
        Binding("plus", "volume_action('up')", "Vol+"),
        Binding("equals", "volume_action('up')", "", show=False),
        Binding("minus", "volume_action('down')", "Vol-"),
        Binding("0", "volume_action('mute')", "Mute"),
        Binding("P", "power_toggle", "Power", key_display="P"),
        Binding("r", "reconnect", "Reconnect"),
        Binding("question_mark", "show_help", "?"),
        Binding("t", "toggle_dark", "Theme"),
        Binding("q", "quit", "Quit", priority=True),
    ]

    atv: Any = None
    connected: reactive[bool] = reactive(False)
    device_name: reactive[str] = reactive("")

    def __init__(self, device_id: str | None = None, host: str | None = None):
        super().__init__()
        self._device_id = device_id
        self._host = host
        self._poll_timer = None
        self._caps = DeviceCaps()
        self._vol_last_action: float = 0.0
        self._vol_cooldown: float = 0.15
        self._push_listener = None
        self._pre_mute_volume: float = 50.0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("Connecting...", id="conn-bar")

        with Vertical(id="col-left"):
            yield RemotePanel()
            yield NowPlaying()

        with Vertical(id="col-right"):
            yield AppsPanel()

        with Horizontal(id="bottom-bar"):
            with Vertical(id="bottom-sys"):
                yield SystemInfo()
            with Vertical(id="bottom-log"):
                yield Label("Log", id="log-title")
                yield ActivityLog(id="log", markup=True)

        yield Footer()

    def on_mount(self) -> None:
        self._log("Starting...")
        if not self._device_id and not self._host:
            config = load_config()
            devs = list_devices(config)
            if len(devs) > 1:
                def on_select(did: str | None) -> None:
                    if did:
                        self._device_id = did
                    self.connect_to_device()
                self.push_screen(DeviceSelectScreen(devs), on_select)
                return
            if not devs:
                self._log("[yellow]No devices paired. Run: atv add[/]")
                return
        self.connect_to_device()

    @work(exclusive=True)
    async def connect_to_device(self) -> None:
        self._log("Scanning...")
        try:
            self.atv = await connect_device(self._device_id, self._host)
            config = load_config()
            dev = get_device(config, self._device_id)
            self.device_name = dev.get("name", "Apple TV") if dev else "Apple TV"
            self.connected = True
            self._log(f"Connected to [bold]{self.device_name}[/]")

            self._caps = DeviceCaps.from_atv(self.atv)

            np_widget = self.query_one(NowPlaying)
            np_widget.display = self._caps.has_title

            if not self._caps.has_title:
                self._log("[dim]Metadata needs airplay — run: atv add[/]")

            await self._update_now_playing()
            await self._update_volume()
            await self._load_system_info(config)
            await self._load_apps()
            self._setup_push_updates()
            self._poll_timer = self.set_interval(5.0, self._poll_status)
        except Exception as e:
            self._log(f"[red]Connection failed:[/] {e}")
            self.connected = False

    def _setup_push_updates(self) -> None:
        if not self.atv or not self._caps.has_push:
            return
        try:
            self._push_listener = PushListener(self._on_push_update)
            self.atv.push_updater.listener = self._push_listener
            self.atv.push_updater.start()
        except Exception:
            pass

    def _on_push_update(self, playing) -> None:
        try:
            self.call_from_thread(self._apply_playing, playing)
        except Exception:
            pass

    def _apply_playing(self, playing) -> None:
        try:
            np = self.query_one(NowPlaying)
            np.title = playing.title or "Nothing Playing"
            np.artist = playing.artist or ""
            np.state = getattr(playing.device_state, "name", str(playing.device_state))
            np.position = playing.position or 0
            np.duration = playing.total_time or 0
            shuf = playing.shuffle
            np.shuffle = getattr(shuf, "name", "") if shuf else ""
            rep = playing.repeat
            np.repeat = getattr(rep, "name", "") if rep else ""
            try:
                app_info = self.atv.metadata.app if self.atv else None
                if app_info:
                    np.app_name = f"{app_info.name} ({app_info.identifier})"
            except Exception:
                pass
        except Exception:
            pass

    def watch_connected(self, value: bool) -> None:
        try:
            bar = self.query_one("#conn-bar", Label)
            if value:
                bar.update(f"Connected: {self.device_name}")
                bar.remove_class("err")
                bar.add_class("ok")
            else:
                bar.update("Disconnected" if self.device_name else "Connecting...")
                bar.remove_class("ok")
                bar.add_class("err")
        except Exception:
            pass

    async def _poll_status(self) -> None:
        if not self.atv or not self.connected:
            return
        try:
            await self._update_volume()
            if not self._push_listener:
                await self._update_now_playing()
        except (ConnectionError, OSError, asyncio.TimeoutError, BrokenPipeError):
            self.connected = False
            self._log("[yellow]Reconnecting...[/]")
            self.connect_to_device()
        except Exception:
            pass

    async def _update_now_playing(self) -> None:
        if not self.atv:
            return
        try:
            playing = await self.atv.metadata.playing()
            self._apply_playing(playing)
        except Exception:
            pass

    async def _update_volume(self) -> None:
        if not self.atv or not self._caps.has_volume_read:
            return
        try:
            vol = self.atv.audio.volume or 0
            # No separate volume widget — volume is in RemotePanel
        except Exception:
            pass

    async def _load_system_info(self, config: dict | None = None) -> None:
        if not self.atv:
            return
        try:
            di = self.atv.device_info
            if not config:
                config = load_config()
            dev = get_device(config, self._device_id)
            info = {
                "Name": dev.get("name", "?") if dev else "?",
                "Model": getattr(di, "model_str", None) or str(di.model),
                "OS": f"{getattr(di.operating_system, 'name', '?')} {di.version or ''}",
                "IP": dev.get("address", "--") if dev else "--",
            }
            self.query_one(SystemInfo).set_info(info)
        except Exception:
            pass

    async def _load_apps(self) -> None:
        if not self.atv:
            return
        try:
            app_list = await self.atv.apps.app_list()
            self.query_one(AppsPanel).set_apps(app_list)
            self._log(f"Loaded {len(app_list)} apps")
        except Exception:
            self._log("[dim]Apps not available[/]")

    async def action_remote(self, command: str) -> None:
        if not self.atv:
            return
        feat_name = _CMD_FEATURE_MAP.get(command)
        if feat_name and not self._caps.is_available(feat_name):
            return
        try:
            method = getattr(self.atv.remote_control, command, None)
            if method:
                await method()
        except Exception as e:
            if "not supported" in str(e).lower():
                return
            self._log(f"[red]{command}: {e}[/]")

    async def action_volume_action(self, action: str) -> None:
        if not self.atv:
            return
        now = time.monotonic()
        if action != "mute" and (now - self._vol_last_action) < self._vol_cooldown:
            return
        self._vol_last_action = now
        caps = self._caps
        try:
            if action == "mute":
                if caps.has_set_volume:
                    current = self.atv.audio.volume or 0
                    if current > 0:
                        self._pre_mute_volume = current
                        await self.atv.audio.set_volume(0.0)
                    else:
                        await self.atv.audio.set_volume(self._pre_mute_volume)
                return
            if action == "up":
                await self._adjust_volume(+1)
            elif action == "down":
                await self._adjust_volume(-1)
        except Exception:
            pass

    async def _adjust_volume(self, direction: int) -> None:
        caps = self._caps
        step = caps.vol_step * direction
        clamp = min if direction > 0 else max
        limit = 100.0 if direction > 0 else 0.0
        has_rel = caps.has_volume_up if direction > 0 else caps.has_volume_down
        rel_fn = self.atv.audio.volume_up if direction > 0 else self.atv.audio.volume_down

        if caps.has_set_volume and caps.has_volume_read:
            current = self.atv.audio.volume or 0
            await asyncio.wait_for(self.atv.audio.set_volume(clamp(current + step, limit)), timeout=3.0)
        elif has_rel:
            asyncio.ensure_future(rel_fn())
        elif caps.has_set_volume:
            await asyncio.wait_for(self.atv.audio.set_volume(50.0), timeout=3.0)
        else:
            try:
                asyncio.ensure_future(rel_fn())
            except Exception:
                pass

    async def action_toggle_shuffle(self) -> None:
        if not self.atv or not self._caps.has_shuffle:
            return
        try:
            from pyatv.const import ShuffleState
            current = self.query_one(NowPlaying).shuffle
            if current == "Off" or not current:
                await self.atv.remote_control.set_shuffle(ShuffleState.Songs)
            else:
                await self.atv.remote_control.set_shuffle(ShuffleState.Off)
        except Exception:
            pass

    async def action_cycle_repeat(self) -> None:
        if not self.atv or not self._caps.has_repeat:
            return
        try:
            from pyatv.const import RepeatState
            current = self.query_one(NowPlaying).repeat
            cycle = {"Off": RepeatState.Track, "Track": RepeatState.All}
            await self.atv.remote_control.set_repeat(cycle.get(current, RepeatState.Off))
        except Exception:
            pass

    async def action_power_toggle(self) -> None:
        if not self.atv:
            return
        try:
            power = self.atv.power
            if PowerState and power.power_state == PowerState.On:
                await power.turn_off()
                self._log("Powered OFF")
            else:
                await power.turn_on()
                self._log("Powered ON")
        except Exception as e:
            self._log(f"[red]Power: {e}[/]")

    async def action_reconnect(self) -> None:
        self._log("Reconnecting...")
        if self.atv:
            try:
                self.atv.push_updater.stop()
            except Exception:
                pass
            try:
                tasks = self.atv.close()
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                pass
            self.atv = None
        self.connected = False
        self._push_listener = None
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None
        self.connect_to_device()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    async def on_remote_panel_remote_command(self, event: RemotePanel.RemoteCommand) -> None:
        await self.action_remote(event.command)

    async def on_remote_panel_power_toggle(self, event: RemotePanel.PowerToggle) -> None:
        await self.action_power_toggle()

    async def on_remote_panel_volume_command(self, event: RemotePanel.VolumeCommand) -> None:
        await self.action_volume_action(event.action)

    async def on_apps_panel_launch_app(self, event: AppsPanel.LaunchApp) -> None:
        if not self.atv:
            return
        try:
            await self.atv.apps.launch_app(event.bundle_id)
            self._log(f"Launched {event.bundle_id}")
        except Exception as e:
            self._log(f"[red]Launch: {e}[/]")

    def _log(self, message: str) -> None:
        try:
            self.query_one("#log", RichLog).write(f"[dim]{ts()}[/] {message}")
        except Exception:
            pass

    def on_unmount(self) -> None:
        if self._poll_timer:
            self._poll_timer.stop()
        if self.atv:
            try:
                self.atv.push_updater.stop()
            except Exception:
                pass
            self.atv.close()


def run_tui(device: str | None = None, host: str | None = None) -> None:
    app = AppleTVApp(device_id=device, host=host)
    app.run()
