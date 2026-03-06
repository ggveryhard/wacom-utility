#!/usr/bin/env python3
"""Wayland Wacom pad mapper using evdev + ydotool."""

import json
import subprocess
import time
from pathlib import Path

import evdev
from evdev import ecodes


CONFIG_PATH = Path.home() / ".wacom_utility_wayland.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {
            "pad_name_contains": "Wacom",
            "mappings": {},
            "strip_mappings": {},
            "strip_scroll": {
                "enabled": False,
                "threshold": 150,
                "multiplier": 3,
                "smoothing": 0.4,
            },
        }
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cfg.setdefault("mappings", {})
        cfg.setdefault("strip_mappings", {})
        had_strip_scroll = "strip_scroll" in cfg
        cfg.setdefault("strip_scroll", {})
        sc = cfg["strip_scroll"]
        sc.setdefault("enabled", bool(cfg["strip_mappings"]) if not had_strip_scroll else True)
        sc.setdefault("threshold", 150)
        sc.setdefault("multiplier", 3)
        sc.setdefault("smoothing", 0.4)
        return cfg
    except Exception:
        return {
            "pad_name_contains": "Wacom",
            "mappings": {},
            "strip_mappings": {},
            "strip_scroll": {
                "enabled": False,
                "threshold": 150,
                "multiplier": 3,
                "smoothing": 0.4,
            },
        }


def remap_raw_button_index(name_hint: str, raw_idx: int) -> int:
    # PTZ-630 / Intuos3 6x8 uses a non-linear order on Wayland:
    # raw 2->0, raw 0->1, raw 1->2, raw 3->3, raw 4->8, raw 5->9, raw 6->A, raw 7->B
    hint = (name_hint or "").lower()
    if "intuos3" in hint and "6x8" in hint:
        mapping = {2: 0, 0: 1, 1: 2, 3: 3, 4: 8, 5: 9, 6: 10, 7: 11}
        return mapping.get(raw_idx, raw_idx)
    return raw_idx


def find_pad_device(name_hint: str) -> evdev.InputDevice | None:
    candidates = []
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except Exception:
            continue
        lname = dev.name.lower()
        if "wacom" in lname and "pad" in lname:
            candidates.append(dev)
            if name_hint.lower() in lname:
                return dev
        else:
            dev.close()
    return candidates[0] if candidates else None


def run_command(command: list[str]) -> None:
    # Backward compatibility: convert legacy wheel-click mapping to mousemove -w.
    if command == ["ydotool", "click", "0xC4"]:
        command = ["ydotool", "mousemove", "-w", "--", "0", "1"]
    elif command == ["ydotool", "click", "0xC5"]:
        command = ["ydotool", "mousemove", "-w", "--", "0", "-1"]

    try:
        subprocess.run(command, check=False, timeout=1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def is_scroll_command(command: list[str]) -> bool:
    return command in (
        ["ydotool", "mousemove", "-w", "--", "0", "1"],
        ["ydotool", "mousemove", "-w", "--", "0", "-1"],
    )


def command_scroll_direction(command: list[str]) -> int:
    if command == ["ydotool", "mousemove", "-w", "--", "0", "1"]:
        return 1
    if command == ["ydotool", "mousemove", "-w", "--", "0", "-1"]:
        return -1
    return 0


def main() -> int:
    last_left = 0
    last_right = 0
    current_pressure = 0
    filtered = 0.0

    while True:
        cfg = load_config()
        name_hint = cfg.get("pad_name_contains", "Wacom")
        mappings = cfg.get("mappings", {})
        strip_mappings = cfg.get("strip_mappings", {})
        has_custom_strip_mappings = any(isinstance(v, dict) for v in strip_mappings.values())
        strip_cfg = cfg.get("strip_scroll", {})
        strip_enabled = bool(strip_cfg.get("enabled", True))
        threshold = int(strip_cfg.get("threshold", 150))
        multiplier = int(strip_cfg.get("multiplier", 3))
        smoothing = float(strip_cfg.get("smoothing", 0.4))
        # evdev ABS codes used by Intuos3 strip from your tray script.
        abs_left_code = 3
        abs_right_code = 4
        abs_pressure_code = 40

        dev = find_pad_device(name_hint)
        if not dev:
            time.sleep(2)
            continue

        try:
            for event in dev.read_loop():
                # Reload config periodically so GUI changes apply without daemon restart.
                if event.sec % 2 == 0:
                    cfg = load_config()
                    mappings = cfg.get("mappings", mappings)
                    strip_mappings = cfg.get("strip_mappings", strip_mappings)
                    has_custom_strip_mappings = any(isinstance(v, dict) for v in strip_mappings.values())
                    strip_cfg = cfg.get("strip_scroll", strip_cfg)
                    strip_enabled = bool(strip_cfg.get("enabled", strip_enabled))
                    threshold = int(strip_cfg.get("threshold", threshold))
                    multiplier = int(strip_cfg.get("multiplier", multiplier))
                    smoothing = float(strip_cfg.get("smoothing", smoothing))

                if event.type == ecodes.EV_KEY and event.value == 1:
                    if ecodes.BTN_0 <= event.code <= ecodes.BTN_9:
                        raw_idx = event.code - ecodes.BTN_0
                        idx = str(remap_raw_button_index(name_hint, raw_idx))
                    elif event.code == getattr(ecodes, "BTN_A", -1):
                        idx = "10"
                    elif event.code == getattr(ecodes, "BTN_B", -1):
                        idx = "11"
                    else:
                        continue

                    action = mappings.get(idx)
                    if not action:
                        continue
                    cmd = action.get("command", [])
                    if isinstance(cmd, list) and cmd:
                        run_command(cmd)

                elif strip_enabled and event.type == ecodes.EV_ABS:
                    if event.code == abs_pressure_code:
                        current_pressure = int(event.value)
                        if current_pressure == 0:
                            last_left = 0
                            last_right = 0
                        continue

                    if event.code not in (abs_left_code, abs_right_code):
                        continue

                    current_val = int(event.value)
                    if event.code == abs_left_code:
                        last_val = last_left
                    else:
                        last_val = last_right

                    if current_val != 0 and last_val != 0:
                        diff = current_val - last_val
                        if abs(diff) > threshold:
                            if current_pressure > 12:
                                speed = 3
                            elif current_pressure > 8:
                                speed = 2
                            else:
                                speed = 1

                            raw_step = speed if diff > 0 else -speed
                            filtered = filtered * smoothing + raw_step * (1.0 - smoothing)
                            slot = None
                            if event.code == abs_left_code:
                                slot = "left_up" if diff > 0 else "left_down"
                            elif event.code == abs_right_code:
                                slot = "right_up" if diff > 0 else "right_down"

                            action = strip_mappings.get(slot) if slot else None
                            if isinstance(action, dict):
                                cmd = action.get("command", [])
                                if isinstance(cmd, list) and is_scroll_command(cmd):
                                    direction = command_scroll_direction(cmd)
                                    wheel_delta = int(abs(filtered) * multiplier) * direction
                                    if wheel_delta != 0:
                                        run_command(["ydotool", "mousemove", "-w", "--", "0", str(wheel_delta)])
                                elif isinstance(cmd, list) and cmd:
                                    run_command(cmd)
                            elif not has_custom_strip_mappings:
                                wheel_delta = int(filtered * multiplier)
                                if wheel_delta != 0:
                                    run_command(["ydotool", "mousemove", "-w", "--", "0", str(wheel_delta)])

                            if event.code == abs_left_code:
                                last_left = current_val
                            else:
                                last_right = current_val

                    elif current_val != 0 and last_val == 0:
                        if event.code == abs_left_code:
                            last_left = current_val
                        else:
                            last_right = current_val
        except Exception:
            time.sleep(1)
            continue


if __name__ == "__main__":
    raise SystemExit(main())
