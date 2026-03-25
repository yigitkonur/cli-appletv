# cli-appletv

apple tv remote control from the terminal. full tui with d-pad, volume, app launcher, and playback controls.

built on [pyatv](https://github.com/postlund/pyatv) + [textual](https://github.com/Textualize/textual).

## install

### macos / linux

```bash
pipx install cli-appletv
```

one-liner (installs pipx + cli-appletv in one shot):

```bash
python3 -m pip install --user pipx && python3 -m pipx ensurepath && python3 -m pipx install cli-appletv
```

### windows

```powershell
pip install pipx && pipx ensurepath && pipx install cli-appletv
```

### homebrew users

```bash
brew install pipx && pipx ensurepath && pipx install cli-appletv
```

### or just pip

```bash
pip install cli-appletv
```

after install, restart your terminal (or run `source ~/.zshrc` / `source ~/.bashrc`) so `atv` is on your PATH.

## setup

```bash
atv add       # scan network, pair your apple tv (all protocols)
atv           # launch the remote
```

that's it. `atv add` pairs both companion (remote control) and airplay (now-playing metadata) automatically.

## usage

just run `atv` — it opens the full-screen tui remote:

```
┌─────────────────────────────────┬──────────────┐
│         ▲                       │ Apps         │
│    ◄   OK   ►                   │  YouTube     │
│         ▼                       │  Netflix     │
│                                 │  Spotify     │
│   Prev  Play  Next  Stop        │  Disney+     │
│   Home  Menu  Power             │  ...         │
│                                 │              │
│        Volume                   │              │
│     -    +    Mute              │              │
├─────────────────┬───────────────┘              │
│ System          │ Log                          │
│ Living Room     │ Connected to Living Room     │
│ Apple TV 4K     │ Loaded 22 apps               │
└─────────────────┴──────────────────────────────┘
```

### keyboard shortcuts

| key | action |
|-----|--------|
| arrows / wasd | d-pad navigation |
| enter / o | select |
| esc / backspace / b | back (menu) |
| h | home |
| space | play/pause |
| s | stop |
| n / p | next / previous |
| + / - | volume up / down |
| 0 | mute toggle |
| P | power on/off |
| ? | help overlay |
| q | quit |

mouse clicks work on all buttons and the apps list.

### cli commands

```bash
atv              # launch tui (default)
atv add          # add/pair apple tv
atv remove       # remove paired device
atv scan         # discover apple tvs on network
atv power status # check power state
atv remote play  # send play command
atv audio up     # volume up
atv apps list    # list installed apps
atv shell        # interactive repl
atv --help       # all commands
```

## volume on apple tv 4k

volume control uses relative mode (up/down steps) on most setups connected via hdmi. this is a [known pyatv limitation](https://github.com/postlund/pyatv/issues/1838) — the companion protocol sends HID key events but can't read volume back from hdmi-cec receivers.

the tui handles this with fire-and-forget volume commands (no timeout errors).

## requirements

- python 3.11+
- apple tv on the same network

## license

mit
