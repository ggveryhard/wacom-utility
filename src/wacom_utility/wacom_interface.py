"""Wacom backend helpers for X11 and Wayland sessions."""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .resources import data_path


@dataclass
class DeviceInfo:
    name: str
    identifier: str
    source: str


class XSetWacom:
    def __init__(self):
        self.session_type = (os.environ.get("XDG_SESSION_TYPE") or "unknown").lower()
        self.has_xsetwacom = shutil.which("xsetwacom") is not None
        self.has_swaymsg = shutil.which("swaymsg") is not None
        self.has_ydotool = shutil.which("ydotool") is not None
        self.use_xsetwacom = self.has_xsetwacom and self.session_type != "wayland"

    def _run(self, command: List[str], timeout: int = 3) -> Optional[subprocess.CompletedProcess]:
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return None

    def _list_from_xsetwacom(self) -> List[DeviceInfo]:
        if not self.use_xsetwacom:
            return []
        proc = self._run(["xsetwacom", "--list", "devices"])
        if not proc or proc.returncode != 0:
            return []

        devices: List[DeviceInfo] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            name = line.split("\tid:")[0].strip()
            devices.append(DeviceInfo(name=name, identifier=name, source="xsetwacom"))
        return devices

    def _list_from_sway(self) -> List[DeviceInfo]:
        proc = self._run(["swaymsg", "-t", "get_inputs", "-r"])
        if not proc or proc.returncode != 0:
            return []

        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return []

        devices: List[DeviceInfo] = []
        for item in payload:
            identifier = item.get("identifier", "")
            name = item.get("name", "")
            merged = f"{name} {identifier}".lower()
            if "wacom" not in merged:
                continue
            shown_name = name or identifier
            if not shown_name:
                continue
            devices.append(DeviceInfo(name=shown_name, identifier=identifier or shown_name, source="sway"))
        return devices

    def list_devices(self) -> List[DeviceInfo]:
        devices = self._list_from_xsetwacom()
        if devices:
            return devices

        # Fallback for Wayland compositors that support sway IPC.
        devices = self._list_from_sway()
        return devices

    def listInterfaces(self) -> List[str]:
        return [device.name for device in self.list_devices()]

    def describe_backend(self) -> str:
        if self.session_type == "wayland" and self.has_swaymsg and self.has_ydotool:
            return "swaymsg + ydotool (Wayland)"
        if self.session_type == "wayland" and self.has_swaymsg:
            return "swaymsg (Wayland)"
        if self.use_xsetwacom:
            return "xsetwacom (X11-compatible)"
        return "no backend tool found"

    def supports_sway_mapping(self) -> bool:
        return self.session_type == "wayland" and self.has_swaymsg

    def build_map_command(self, identifier: str, output: str) -> List[str]:
        return ["swaymsg", "input", identifier, "map_to_output", output]

    def map_to_output(self, identifier: str, output: str) -> Tuple[bool, str]:
        if not self.supports_sway_mapping():
            return False, "Wayland mapping requires swaymsg in a Wayland session."
        proc = self._run(self.build_map_command(identifier, output))
        if not proc:
            return False, "Failed to run swaymsg."
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "swaymsg returned non-zero status").strip()
            return False, message
        return True, (proc.stdout or "ok").strip()

    def map_to_all_outputs(self, identifier: str) -> Tuple[bool, str]:
        return self.map_to_output(identifier, "*")

    def getConfiguration(self, device: str, function: str) -> str:
        if not self.use_xsetwacom:
            return ""
        proc = self._run(["xsetwacom", "get", device, function])
        if not proc:
            return ""
        return proc.stdout.strip()

    def setConfiguration(self, device: str, function: str, value: str) -> bool:
        if not self.use_xsetwacom:
            return False
        proc = self._run(["xsetwacom", "set", device, function, value])
        return bool(proc and proc.returncode == 0)

    def get_pressure_curve(self, device: str) -> Optional[List[float]]:
        raw = self.getConfiguration(device, "PressureCurve")
        if not raw:
            return None
        bits = raw.split()
        if len(bits) != 4:
            return None
        try:
            return [float(x) for x in bits]
        except ValueError:
            return None

    def set_pressure_curve(self, device: str, points: List[float]) -> bool:
        if len(points) != 4 or not self.use_xsetwacom:
            return False
        args = [str(float(p)) for p in points]
        proc = self._run(["xsetwacom", "set", device, "PressureCurve", *args])
        return bool(proc and proc.returncode == 0)

    def get_click_force(self, device: str) -> Optional[float]:
        raw = self.getConfiguration(device, "Threshold")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def set_click_force(self, device: str, force: float) -> bool:
        return self.setConfiguration(device, "Threshold", str(float(force)))

    def get_mode(self, device: str) -> str:
        return self.getConfiguration(device, "Mode")

    def set_mode(self, device: str, mode: str) -> bool:
        return self.setConfiguration(device, "Mode", mode)

    def listModifiers(self) -> List[Tuple[str, str]]:
        keymap_path = data_path("keymap.txt")
        try:
            lines = keymap_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        ret: List[Tuple[str, str]] = []
        for line in lines:
            if not line or line.startswith("#") or "\t" not in line:
                continue
            key, label = line.split("\t", 1)
            ret.append((key.strip(), label.strip()))
        return ret

    def listMouseActions(self) -> List[Tuple[str, str]]:
        return [
            ("button 1", "Left Click"),
            ("button 2", "Right Click"),
            ("button 3", "Middle Click"),
            ("button 4", "Scroll Wheel Up"),
            ("button 5", "Scroll Wheel Down"),
            ("DBLCLICK 1", "Double Click"),
        ]

    def lookUpMouseName(self, name: str) -> str:
        for raw, label in self.listMouseActions():
            if label == name:
                return raw
        return "button 1"

    def lookUpMouseButton(self, button: str) -> str:
        mapping = {
            "1": "Left Click",
            "2": "Right Click",
            "3": "Middle Click",
            "4": "Scroll Wheel Up",
            "5": "Scroll Wheel Down",
        }
        return mapping.get(button, button)

    def verifyString(self, string: str) -> bool:
        if any(ch in string for ch in ["'", "\"", "\\", "\t"]):
            return False
        valid = {key.upper() for key, _ in self.listModifiers()}
        for item in string.split():
            if len(item) <= 1:
                continue
            if item.upper() not in valid:
                return False
        return True

    def getTypeAndName(self, device: str, button_callsign: str) -> Tuple[int, str]:
        # 0 = Ignore, 1 = Mouse, 2 = Key
        data = self.getConfiguration(device, button_callsign)
        if not data or data == "0":
            return 0, "Ignore"
        upper = data.upper()
        if upper.startswith("DBLCLICK"):
            return 1, "Double Click"
        if upper.startswith("BUTTON "):
            return 1, self.lookUpMouseButton(data.split()[-1])
        if data.isdigit():
            return 1, self.lookUpMouseButton(data)
        if upper.startswith("CORE KEY "):
            return 2, data[9:]
        return 2, data

    def setByTypeAndName(
        self,
        device: str,
        button_callsign: str,
        action_type: int,
        name: str = "",
    ) -> bool:
        if not self.use_xsetwacom:
            return False
        if action_type == 0:
            value = "0"
        elif action_type == 1:
            value = self.lookUpMouseName(name)
        elif action_type == 2:
            value = f"CORE KEY {name.strip()}"
        else:
            return False
        proc = self._run(["xsetwacom", "set", device, button_callsign, value])
        return bool(proc and proc.returncode == 0)
