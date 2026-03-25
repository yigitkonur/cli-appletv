# pyatv-cli

apple tv remote control from the terminal. full tui with d-pad, volume, app launcher, and playback controls.

built on [pyatv](https://github.com/postlund/pyatv) + [textual](https://github.com/Textualize/textual).

## install

```bash
pipx install pyatv-cli
```

or with pip:

```bash
pip install pyatv-cli
```

**one-liner** (installs pipx if needed, then pyatv-cli):

```bash
python3 -m pip install --user pipx && python3 -m pipx install pyatv-cli
```

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
├─────────────────┬───────────────┤              │
│ System          │ Log           │              │
│ Living Room     │ Connected     │              │
│ Apple TV 4K     │ Vol +         │              │
└─────────────────┴───────────────┘              │
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

volume control uses relative mode (up/down steps) on most apple tv setups connected via hdmi. this is a [known pyatv limitation](https://github.com/postlund/pyatv/issues/1838) — the companion protocol sends HID key events but can't read the current volume level back from hdmi-cec receivers.

the tui handles this correctly with fire-and-forget volume commands (no timeout errors).

## requirements

- python 3.11+
- apple tv on the same network

## license

mit
