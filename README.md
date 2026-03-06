# Wacom Utility (GTK4 + Wayland)

Modernized Wacom utility with:
- GTK4 GUI (`wacom-utility`)
- Wayland backend via `evdev + ydotool` (`wacom-wayland-pad-daemon`)
- X11 fallback for `xsetwacom` where available

## Current Architecture

- Frontend: `wacom-utility`
  - Device list, pad layout, mapping UI
  - Writes Wayland mappings to `~/.wacom_utility_wayland.json`
- Backend daemon: `wacom-wayland-pad-daemon`
  - Reads pad events from `evdev`
  - Executes mapped actions through `ydotool`
  - Supports strip scrolling (`EV_ABS`) with threshold/smoothing/multiplier

## Dependencies

### Common
- Python 3.10+
- `python3-gi` / GTK4 runtime
- `python3-cairo`
- `python3-evdev`

### Wayland (sway/wlroots path)
- `ydotool`
- `ydotoold` running in user session
- `swaymsg` (for output mapping in GUI)

### X11
- `xsetwacom` (`wacom-tools`)

## Run

PyPI-style user install:

```bash
python3 -m pip install --user .
```

This installs console entry points to:
- `~/.local/bin/wacom-utility`
- `~/.local/bin/wacom-wayland-pad-daemon`

The Python package and bundled UI/images/XML are installed under the user
site-packages directory, typically:
- `~/.local/lib/python3.x/site-packages/wacom_utility`

That is the standard Python packaging layout. A normal `pip install --user`
does not install package data to `~/.local/share`.

Run after user install:

```bash
wacom-utility
```

Quick environment check:

```bash
wacom-utility --check
```

Source checkout without installation:

```bash
PYTHONPATH=src python3 -m wacom_utility.wacom_utility
```

## Wayland Mapping Flow

1. Open GUI and configure pad buttons (Pad/Edit or Mapping tab).
2. Settings are stored in:
   - `~/.wacom_utility_wayland.json`
3. Start daemon:

```bash
wacom-wayland-pad-daemon
```

Source checkout without installation:

```bash
PYTHONPATH=src python3 -m wacom_utility.wayland_pad_daemon
```

### Strip scroll tuning

`~/.wacom_utility_wayland.json` supports:

```json
{
  "strip_scroll": {
    "enabled": true,
    "threshold": 150,
    "multiplier": 3,
    "smoothing": 0.4
  }
}
```

## systemd --user (Auto-start daemon)

For PyPI-style user installs, the repo user unit targets:
- `%h/.local/bin/wacom-wayland-pad-daemon`

Service file included:
- `systemd/user/wacom-wayland-pad-daemon.service`

Both the repo user unit and the RPM unit are rendered from the shared template:
- `systemd/wacom-wayland-pad-daemon.service.in`

User install flow:

```bash
python3 -m pip install --user .
mkdir -p ~/.config/systemd/user
cp systemd/user/wacom-wayland-pad-daemon.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now wacom-wayland-pad-daemon.service
```

For RPM installs, the packaged user unit targets the system wrapper:
- `/usr/bin/wacom-wayland-pad-daemon`

RPM install:

```bash
systemctl --user daemon-reload
systemctl --user enable --now wacom-wayland-pad-daemon.service
```

Source checkout:

Do not use the bundled user unit directly from a source checkout unless you have
already installed the package to `~/.local/bin`. Otherwise run the daemon
directly from the repo:

```bash
PYTHONPATH=src python3 -m wacom_utility.wayland_pad_daemon
```

Check status/logs:

```bash
systemctl --user status wacom-wayland-pad-daemon.service
journalctl --user -u wacom-wayland-pad-daemon.service -f
```

Disable:

```bash
systemctl --user disable --now wacom-wayland-pad-daemon.service
```
