# Wacom Utility (GTK4 + Wayland)

Modernized Wacom utility with:
- GTK4 GUI (`wacom_utility.py`)
- Wayland backend via `evdev + ydotool` (`wayland_pad_daemon.py`)
- X11 fallback for `xsetwacom` where available

## Current Architecture

- Frontend: `wacom_utility.py`
  - Device list, pad layout, mapping UI
  - Writes Wayland mappings to `~/.wacom_utility_wayland.json`
- Backend daemon: `wayland_pad_daemon.py`
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

```bash
python3 wacom_utility.py
```

Quick environment check:

```bash
python3 wacom_utility.py --check
```

## Wayland Mapping Flow

1. Open GUI and configure pad buttons (Pad/Edit or Mapping tab).
2. Settings are stored in:
   - `~/.wacom_utility_wayland.json`
3. Start daemon:

```bash
python3 wayland_pad_daemon.py
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

Service file included:
- `systemd/user/wacom-wayland-pad-daemon.service`

Install and enable:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/user/wacom-wayland-pad-daemon.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now wacom-wayland-pad-daemon.service
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
