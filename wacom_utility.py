#!/usr/bin/env python3
"""GTK4 Wacom utility, legacy GUI style with Wayland support."""

import os
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from cairo_framework import Pad
from wacom_identify import TabletIdClass
from wacom_interface import DeviceInfo, XSetWacom


CONFIG_PATH = Path.home() / ".wacom_utility"
WAYLAND_CONFIG_PATH = Path.home() / ".wacom_utility_wayland.json"


def resolve_data_dir() -> Path:
    app_dir = Path(__file__).resolve().parent
    candidates = [
        Path(os.environ.get("WACOM_UTILITY_DATA_DIR", "")) if os.environ.get("WACOM_UTILITY_DATA_DIR") else None,
        app_dir,
        Path("/usr/share/wacom-utility"),
    ]
    for c in candidates:
        if c and (c / "wacom_utility_gtk4.ui").exists():
            return c
    return app_dir


DATA_DIR = resolve_data_dir()
os.environ.setdefault("WACOM_UTILITY_DATA_DIR", str(DATA_DIR))
UI_PATH = DATA_DIR / "wacom_utility_gtk4.ui"


KEYCODE_MAP = {
    "CTRL": 29,
    "CONTROL": 29,
    "SHIFT": 42,
    "ALT": 56,
    "SUPER": 125,
    "META": 125,
    "SPACE": 57,
    "TAB": 15,
    "ENTER": 28,
    "ESC": 1,
    "BACKSPACE": 14,
}

for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=0):
    KEYCODE_MAP[ch] = [30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44][i]

for i in range(1, 10):
    KEYCODE_MAP[str(i)] = i + 1
KEYCODE_MAP["0"] = 11

for i in range(1, 13):
    KEYCODE_MAP[f"F{i}"] = 58 + i
KEYCODE_MAP["PAGEUP"] = 104
KEYCODE_MAP["PAGEDOWN"] = 109


# Wayland tablet-pad index mapping (libinput TABLET_PAD_BUTTON index).
# Intuos3 PTZ-630 mapping follows the diagram from wacom.sh.
WAYLAND_INDEX_MAP_BY_MODEL = {
    "PTZ-630": {
        "Button3": 0,
        "Button1": 1,
        "Button2": 2,
        "Button4": 3,
        "striplup": 4,
        "stripldn": 5,
        "striprup": 6,
        "striprdn": 7,
        "Button5": 8,
        "Button6": 9,
        "Button7": 10,
        "Button8": 11,
        # Legacy aliases kept for compatibility with old naming/docs.
        "Button9": 8,
        "Button10": 9,
        "Button11": 10,
        "Button12": 11,
    }
}


def ensure_config_file() -> None:
    if CONFIG_PATH.exists():
        return
    CONFIG_PATH.write_text("configureonlogin=1\n", encoding="utf-8")


def read_configure_on_login() -> bool:
    ensure_config_file()
    for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("configureonlogin="):
            return line.split("=", 1)[1].strip() == "1"
    return True


def write_configure_on_login(active: bool) -> None:
    ensure_config_file()
    lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not line.startswith("configureonlogin=")]
    kept.insert(0, f"configureonlogin={1 if active else 0}")
    CONFIG_PATH.write_text("\n".join(kept) + "\n", encoding="utf-8")


def run_configure_mode() -> int:
    ensure_config_file()
    lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    if not read_configure_on_login():
        return 0

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("configureonlogin="):
            continue
        subprocess.run(line, shell=True, check=False)
    return 0


def load_wacom_ascii_diagram() -> str:
    src = Path("/home/sam/Downloads/wacom.sh")
    if src.exists():
        try:
            lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
            block = []
            keep = False
            for line in lines:
                if line.startswith("#    Wacom Intuos3 6x8 pad"):
                    keep = True
                if keep and line.startswith("# More info:"):
                    break
                if keep:
                    if line.startswith("#"):
                        block.append(line[1:])
                    else:
                        block.append(line)
            text = "\n".join(block).strip("\n")
            if text.strip():
                return text
        except Exception:
            pass

    return (
        " Wacom Intuos3 6x8 pad\n"
        " _________________________________________________________________________\n"
        "| 0-Button0  1-Button1  2-Button2  3-Button3  4-StripLeftUp  5-StripLeftDown |\n"
        "| 6-StripRightUp  7-StripRightDown  8-Button8  9-Button9  A-ButtonA  B-ButtonB |\n"
    )


def load_wayland_config() -> dict:
    if not WAYLAND_CONFIG_PATH.exists():
        return {"pad_name_contains": "Wacom", "mappings": {}}
    try:
        return json.loads(WAYLAND_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"pad_name_contains": "Wacom", "mappings": {}}


def save_wayland_config(config: dict) -> None:
    WAYLAND_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def key_sequence_to_ydotool_command(sequence: str) -> list[str] | None:
    tokens = [t.strip().upper() for t in sequence.split() if t.strip()]
    if not tokens:
        return None
    modifier_tokens = {"CTRL", "CONTROL", "SHIFT", "ALT", "SUPER", "META"}
    modifiers: list[int] = []
    normals: list[int] = []

    for token in tokens:
        code = KEYCODE_MAP.get(token)
        if code is None:
            return None
        if token in modifier_tokens:
            modifiers.append(code)
        else:
            normals.append(code)

    if not normals:
        # Keep previous behavior for modifier-only mappings.
        normals = modifiers[:]
        modifiers = []

    args = []
    for code in modifiers:
        args.append(f"{code}:1")
    for code in normals:
        args.append(f"{code}:1")
    for code in reversed(normals):
        args.append(f"{code}:0")
    for code in reversed(modifiers):
        args.append(f"{code}:0")
    return ["ydotool", "key", *args]


def wayland_mouse_command(label: str) -> list[str] | None:
    # For wheel actions, prefer mousemove -w because it is more reliable on Wayland.
    mapping = {
        "Left Click": ["ydotool", "click", "0xC0"],
        "Right Click": ["ydotool", "click", "0xC1"],
        "Middle Click": ["ydotool", "click", "0xC2"],
        "Scroll Wheel Up": ["ydotool", "mousemove", "-w", "--", "0", "1"],
        "Scroll Wheel Down": ["ydotool", "mousemove", "-w", "--", "0", "-1"],
    }
    if label == "Double Click":
        return ["ydotool", "click", "--repeat", "2", "--delay", "10", "0xC0"]
    return mapping.get(label)


def wayland_button_index(model: str | None, callsign: str, number: str | int) -> int | None:
    if model and model in WAYLAND_INDEX_MAP_BY_MODEL:
        idx = WAYLAND_INDEX_MAP_BY_MODEL[model].get(callsign)
        if idx is not None:
            return idx
        # PTZ-630 XML now stores direct libinput-style indices (0..B).
        if model == "PTZ-630":
            s = str(number).strip().upper()
            try:
                return int(s, 16)
            except Exception:
                pass
    try:
        n = int(number)
        return max(0, n - 1)
    except Exception:
        return None


class ButtonMappingDialog(Gtk.Window):
    def __init__(
        self,
        parent: Gtk.Window,
        backend: XSetWacom,
        device_id: str | None,
        pad_name: str | None,
        tablet_model: str | None,
        button_obj,
    ):
        super().__init__(title="Modify Button Action")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(520, 320)

        self.backend = backend
        self.device_id = device_id
        self.pad_name = pad_name or "Wacom"
        self.tablet_model = tablet_model
        self.button_obj = button_obj
        self.mouse_actions = backend.listMouseActions()
        self.special_keys = backend.listModifiers()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        self.set_child(root)

        header = Gtk.Label()
        header.set_markup(
            f"<b>Modifying Action for Button {button_obj.Number} ({button_obj.Callsign})</b>"
        )
        header.set_xalign(0.0)
        root.append(header)

        self.rb_ignore = Gtk.CheckButton(label="Ignore")
        self.rb_mouse = Gtk.CheckButton(label="Mouse Button")
        self.rb_mouse.set_group(self.rb_ignore)
        self.rb_key = Gtk.CheckButton(label="Key Stroke")
        self.rb_key.set_group(self.rb_ignore)
        self.rb_ignore.set_active(True)

        root.append(self.rb_ignore)
        root.append(self.rb_mouse)
        root.append(self.rb_key)

        self.mouse_values = [label for _, label in self.mouse_actions]
        self.mouse_dropdown = Gtk.DropDown.new_from_strings(self.mouse_values)
        root.append(self.mouse_dropdown)

        key_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.append(key_box)

        self.key_entry = Gtk.Entry()
        self.key_entry.set_hexpand(True)
        self.key_entry.set_placeholder_text("Enter key sequence, e.g. CTRL Z")
        key_box.append(self.key_entry)

        self.special_key_values = [key for key, _ in self.special_keys]
        self.special_key_labels = [f"{key} - {label}" for key, label in self.special_keys]
        self.special_key_dropdown = Gtk.DropDown.new_from_strings(
            self.special_key_labels if self.special_key_labels else ["No keys"]
        )
        key_box.append(self.special_key_dropdown)

        self.add_key_btn = Gtk.Button(label="Add")
        key_box.append(self.add_key_btn)

        self.status = Gtk.Label()
        self.status.set_xalign(0.0)
        self.status.set_wrap(True)
        root.append(self.status)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_halign(Gtk.Align.END)
        root.append(btn_row)

        self.cancel_btn = Gtk.Button(label="Close")
        self.apply_btn = Gtk.Button(label="Apply")
        btn_row.append(self.cancel_btn)
        btn_row.append(self.apply_btn)

        self.rb_ignore.connect("toggled", self.on_type_toggle)
        self.rb_mouse.connect("toggled", self.on_type_toggle)
        self.rb_key.connect("toggled", self.on_type_toggle)
        self.add_key_btn.connect("clicked", self.on_add_key)
        self.cancel_btn.connect("clicked", lambda _b: self.close())
        self.apply_btn.connect("clicked", self.on_apply)

        self.load_current()
        self.on_type_toggle(self.rb_ignore)

    def on_type_toggle(self, _button: Gtk.CheckButton) -> None:
        mouse_mode = self.rb_mouse.get_active()
        key_mode = self.rb_key.get_active()
        self.mouse_dropdown.set_sensitive(mouse_mode)
        self.key_entry.set_sensitive(key_mode)
        self.special_key_dropdown.set_sensitive(key_mode and bool(self.special_key_values))
        self.add_key_btn.set_sensitive(key_mode and bool(self.special_key_values))

    def on_add_key(self, _button: Gtk.Button) -> None:
        if not self.special_key_values:
            return
        idx = int(self.special_key_dropdown.get_selected())
        if idx < 0 or idx >= len(self.special_key_values):
            return
        token = self.special_key_values[idx]
        old = self.key_entry.get_text().strip()
        self.key_entry.set_text(f"{old} {token}".strip())

    def load_current(self) -> None:
        if self.backend.session_type == "wayland":
            idx = wayland_button_index(self.tablet_model, self.button_obj.Callsign, self.button_obj.Number)
            if idx is None:
                self.status.set_text("Unsupported button index for Wayland mapping.")
                return
            cfg = load_wayland_config()
            action = cfg.get("mappings", {}).get(str(idx))
            if not action:
                self.rb_ignore.set_active(True)
                return
            label = action.get("label", "")
            if label in self.mouse_values:
                self.rb_mouse.set_active(True)
                self.mouse_dropdown.set_selected(self.mouse_values.index(label))
            else:
                self.rb_key.set_active(True)
                self.key_entry.set_text(label)
            self.status.set_text(f"Wayland idx {idx}")
            return

        if not self.device_id or not self.backend.use_xsetwacom:
            self.status.set_text("xsetwacom backend unavailable.")
            return

        action_type, action_name = self.backend.getTypeAndName(self.device_id, self.button_obj.Callsign)
        if action_type == 0:
            self.rb_ignore.set_active(True)
            self.key_entry.set_text("")
        elif action_type == 1:
            self.rb_mouse.set_active(True)
            if action_name in self.mouse_values:
                self.mouse_dropdown.set_selected(self.mouse_values.index(action_name))
        else:
            self.rb_key.set_active(True)
            self.key_entry.set_text(action_name)

    def on_apply(self, _button: Gtk.Button) -> None:
        callsign = self.button_obj.Callsign
        if self.backend.session_type == "wayland":
            btn_index = wayland_button_index(self.tablet_model, self.button_obj.Callsign, self.button_obj.Number)
            if btn_index is None:
                self.status.set_text("Unsupported pad button index for Wayland mapper.")
                return

            cfg = load_wayland_config()
            cfg["pad_name_contains"] = self.pad_name
            mappings = cfg.setdefault("mappings", {})
            key = str(btn_index)

            if self.rb_ignore.get_active():
                mappings.pop(key, None)
                save_wayland_config(cfg)
                self.status.set_text(f"Wayland mapping cleared for button index {btn_index}.")
                return

            if self.rb_mouse.get_active():
                idx = int(self.mouse_dropdown.get_selected())
                label = self.mouse_values[idx] if 0 <= idx < len(self.mouse_values) else "Left Click"
                cmd = wayland_mouse_command(label)
                if not cmd:
                    self.status.set_text("This mouse action is not supported in Wayland mapper.")
                    return
                mappings[key] = {"label": label, "command": cmd}
                save_wayland_config(cfg)
                self.status.set_text(
                    f"Saved Wayland mapping for button index {btn_index}. Start wayland_pad_daemon.py."
                )
                return

            keys = self.key_entry.get_text().strip()
            if not keys:
                self.status.set_text("Please enter a key sequence.")
                return
            cmd = key_sequence_to_ydotool_command(keys)
            if not cmd:
                self.status.set_text("Unsupported key token for ydotool conversion.")
                return
            mappings[key] = {"label": keys, "command": cmd}
            save_wayland_config(cfg)
            self.status.set_text(
                f"Saved Wayland mapping for button index {btn_index}. Start wayland_pad_daemon.py."
            )
            return

        if not self.device_id or not self.backend.use_xsetwacom:
            self.status.set_text("xsetwacom backend unavailable.")
            return

        ok = False
        if self.rb_ignore.get_active():
            ok = self.backend.setByTypeAndName(self.device_id, callsign, 0)
        elif self.rb_mouse.get_active():
            idx = int(self.mouse_dropdown.get_selected())
            label = self.mouse_values[idx] if 0 <= idx < len(self.mouse_values) else "Left Click"
            ok = self.backend.setByTypeAndName(self.device_id, callsign, 1, label)
        else:
            keys = self.key_entry.get_text().strip()
            if not keys:
                self.status.set_text("Please enter a key sequence.")
                return
            if not self.backend.verifyString(keys):
                self.status.set_text("Invalid key sequence.")
                return
            ok = self.backend.setByTypeAndName(self.device_id, callsign, 2, keys)

        self.status.set_text("Button mapping updated." if ok else "Failed to update mapping.")


class MainWindow:
    def __init__(self, app: Gtk.Application):
        self.app = app
        self.backend = XSetWacom()
        self.tablet_ident = TabletIdClass()
        self.tablets = self.tablet_ident.identify()

        self.devices: list[DeviceInfo] = []
        self.current_device: DeviceInfo | None = None
        self.current_tablet = None
        self._updating_pressure_ui = False

        self.builder = Gtk.Builder()
        self.builder.add_from_file(str(UI_PATH))

        self.window: Gtk.Window = self.builder.get_object("window1")
        self.window.set_application(app)

        self.stack: Gtk.Stack = self.builder.get_object("right-stack")
        self.stack_switcher: Gtk.StackSwitcher = self.builder.get_object("stack-switcher")
        self.stack_switcher.set_stack(self.stack)
        self._configure_stack_pages()

        self.tablet_label: Gtk.Label = self.builder.get_object("tablet-label")
        self.backend_label: Gtk.Label = self.builder.get_object("backend-label")
        self.session_label: Gtk.Label = self.builder.get_object("session-label")
        self.welcome_text: Gtk.Label = self.builder.get_object("welcome-text")
        self.input_list: Gtk.ListBox = self.builder.get_object("input-list")

        self.applyonstartup: Gtk.CheckButton = self.builder.get_object("applyonstartup")
        self.save_commands: Gtk.CheckButton = self.builder.get_object("save-commands")

        self.output_entry: Gtk.Entry = self.builder.get_object("output-entry")
        self.map_output_btn: Gtk.Button = self.builder.get_object("map-output-btn")
        self.map_all_btn: Gtk.Button = self.builder.get_object("map-all-btn")

        self.touchstrip_left_up_func: Gtk.DropDown = self.builder.get_object("touchstrip-left-up-func")
        self.touchstrip_left_down_func: Gtk.DropDown = self.builder.get_object("touchstrip-left-down-func")
        self.touchstrip_right_up_func: Gtk.DropDown = self.builder.get_object("touchstrip-right-up-func")
        self.touchstrip_right_down_func: Gtk.DropDown = self.builder.get_object("touchstrip-right-down-func")
        self.touchstrip_apply_btn: Gtk.Button = self.builder.get_object("touchstrip-apply-btn")
        self.touchstrip_status: Gtk.Label = self.builder.get_object("touchstrip-status")
        self.mapping_preview_area: Gtk.Box = self.builder.get_object("mapping-preview-area")
        self.mapping_pad_widget = Pad()
        self.mapping_pad_widget.set_content_width(520)
        self.mapping_pad_widget.set_content_height(320)
        self.mapping_pad_widget.set_select_callback(self.on_mapping_preview_selected)
        self.mapping_preview_area.append(self.mapping_pad_widget)

        self.pressure_support: Gtk.Label = self.builder.get_object("pressure-support")
        self.devicemodecombo: Gtk.DropDown = self.builder.get_object("devicemodecombo")
        self.clickforce_scale: Gtk.Scale = self.builder.get_object("clickforce-scale")
        self.cp1x: Gtk.SpinButton = self.builder.get_object("cp1x")
        self.cp1y: Gtk.SpinButton = self.builder.get_object("cp1y")
        self.cp2x: Gtk.SpinButton = self.builder.get_object("cp2x")
        self.cp2y: Gtk.SpinButton = self.builder.get_object("cp2y")
        self.apply_pressure_curve_btn: Gtk.Button = self.builder.get_object("apply-pressure-curve")

        self.map_button_combo: Gtk.DropDown = self.builder.get_object("map-button-combo")
        self.map_type_combo: Gtk.DropDown = self.builder.get_object("map-type-combo")
        self.mouse_action_combo: Gtk.DropDown = self.builder.get_object("mouse-action-combo")
        self.key_action_entry: Gtk.Entry = self.builder.get_object("key-action-entry")
        self.apply_map_btn: Gtk.Button = self.builder.get_object("apply-map-btn")
        self.map_status: Gtk.Label = self.builder.get_object("map-status")

        self.builder.get_object("button-close").connect("clicked", self.on_close)
        self.builder.get_object("button-help").connect("clicked", self.on_help)
        self.builder.get_object("refresh-devices").connect("clicked", self.on_refresh)

        self.input_list.connect("row-selected", self.on_select_device)
        self.applyonstartup.connect("toggled", self.on_toggle_startup)

        self.map_output_btn.connect("clicked", self.on_map_output)
        self.map_all_btn.connect("clicked", self.on_map_all)

        self.devicemodecombo.connect("notify::selected", self.on_mode_changed)
        self.clickforce_scale.connect("value-changed", self.on_click_force_changed)
        self.apply_pressure_curve_btn.connect("clicked", self.on_apply_pressure_curve)
        self.map_type_combo.connect("notify::selected", self.on_map_type_changed)
        self.map_button_combo.connect("notify::selected", self.on_map_button_changed)
        self.apply_map_btn.connect("clicked", self.on_apply_map)
        self.touchstrip_apply_btn.connect("clicked", self.on_touchstrip_apply)

        self.mode_values: list[str] = []
        self.map_type_values: list[str] = []
        self.mouse_action_values: list[str] = []
        self.map_button_values: list[str] = []
        self.touchstrip_action_values: list[str] = []
        self._map_syncing_selection = False

        self._init_mapping_controls()
        self._init_mode_controls()
        self._init_touchstrip_controls()
        self.init_ui()

    def _configure_stack_pages(self) -> None:
        pages = [
            ("WelcomeScreen", "welcome", "Welcome"),
            ("PadContainer", "touchstrip", "Touch Strip"),
            ("PressureContainer", "pen", "Pen"),
            ("MappingContainer", "expresskeys", "ExpressKeys"),
            ("OptionsContainer", "options", "Options"),
        ]
        for obj_id, name, title in pages:
            widget = self.builder.get_object(obj_id)
            if not widget:
                continue
            page = self.stack.get_page(widget)
            if not page:
                continue
            page.set_name(name)
            page.set_title(title)

    def _set_dropdown_items(self, dropdown: Gtk.DropDown, labels: list[str]) -> Gtk.StringList:
        model = Gtk.StringList.new(labels)
        dropdown.set_model(model)
        return model

    def _selected_index(self, dropdown: Gtk.DropDown) -> int:
        idx = int(dropdown.get_selected())
        if idx == Gtk.INVALID_LIST_POSITION:
            return -1
        return idx if idx >= 0 else -1

    def _init_mapping_controls(self) -> None:
        self.map_type_values = ["ignore", "mouse", "key"]
        self._set_dropdown_items(self.map_type_combo, ["Ignore", "Mouse Button", "Key Stroke"])
        self.map_type_combo.set_selected(0)

        mouse_actions = self.backend.listMouseActions()
        self.mouse_action_values = [label for _, label in mouse_actions]
        self._set_dropdown_items(self.mouse_action_combo, self.mouse_action_values)
        self.mouse_action_combo.set_selected(0)
        self.on_map_type_changed(self.map_type_combo)

    def _init_mode_controls(self) -> None:
        self.mode_values = ["Absolute", "Relative"]
        self._set_dropdown_items(self.devicemodecombo, self.mode_values)
        self.devicemodecombo.set_selected(0)
        self.clickforce_scale.set_range(0.0, 100.0)

    def _init_touchstrip_controls(self) -> None:
        self.touchstrip_action_values = [
            "Ignore",
            "Scroll Wheel Up",
            "Scroll Wheel Down",
            "Page Up",
            "Page Down",
            "Left Click",
            "Right Click",
            "Middle Click",
        ]
        for dd in (
            self.touchstrip_left_up_func,
            self.touchstrip_left_down_func,
            self.touchstrip_right_up_func,
            self.touchstrip_right_down_func,
        ):
            self._set_dropdown_items(dd, self.touchstrip_action_values)
            dd.set_selected(0)

    def _touchstrip_slots(self) -> list[tuple[str, Gtk.DropDown, str, str]]:
        return [
            ("Left Up", self.touchstrip_left_up_func, "striplup", "left_up"),
            ("Left Down", self.touchstrip_left_down_func, "stripldn", "left_down"),
            ("Right Up", self.touchstrip_right_up_func, "striprup", "right_up"),
            ("Right Down", self.touchstrip_right_down_func, "striprdn", "right_down"),
        ]

    def _touchstrip_action_to_command(self, action_label: str) -> list[str] | None:
        if action_label == "Ignore":
            return None
        if action_label in ("Page Up", "Page Down"):
            return key_sequence_to_ydotool_command(action_label.upper().replace(" ", ""))
        return wayland_mouse_command(action_label)

    def _touchstrip_command_to_action(self, cmd: list[str] | None, label: str) -> str:
        if not cmd:
            return "Ignore"
        if label in self.touchstrip_action_values:
            return label
        if cmd == ["ydotool", "key", "104:1", "104:0"]:
            return "Page Up"
        if cmd == ["ydotool", "key", "109:1", "109:0"]:
            return "Page Down"
        return "Ignore"

    def _set_touchstrip_dropdown_value(self, dropdown: Gtk.DropDown, action_label: str) -> None:
        if action_label not in self.touchstrip_action_values:
            action_label = "Ignore"
        dropdown.set_selected(self.touchstrip_action_values.index(action_label))

    def init_ui(self) -> None:
        ensure_config_file()
        self.applyonstartup.set_active(read_configure_on_login())

        self.session_label.set_text(f"Session: {os.environ.get('XDG_SESSION_TYPE', 'unknown')}")
        self.backend_label.set_text(f"Backend: {self.backend.describe_backend()}")
        if self.backend.session_type == "wayland":
            self.welcome_text.set_text(
                "Wayland mode: configure pad buttons with Edit, then run: python3 wayland_pad_daemon.py"
            )

        self.refresh_devices()
        self.update_wayland_buttons()
        self.update_pressure_availability()
        self.map_status.set_text("Select a device and button to edit mapping.")
        self.touchstrip_status.set_text("Select actions, then click Apply Touch Strip.")

    def clear_listbox(self, listbox: Gtk.ListBox) -> None:
        child = listbox.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            listbox.remove(child)
            child = nxt

    def refresh_devices(self) -> None:
        self.devices = self.backend.list_devices()
        self.clear_listbox(self.input_list)

        if not self.devices:
            self.current_device = None
            self.current_tablet = None
            self.tablet_label.set_text("No graphics tablets detected")
            self.welcome_text.set_text("No Wacom devices found. Check swaymsg/ydotool (Wayland) or xsetwacom (X11).")
            self.refresh_pad_page()
            self.refresh_mapping_controls()
            self.refresh_pressure_page()
            return

        for dev in self.devices:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=f"{dev.name} [{dev.source}]")
            label.set_xalign(0.0)
            row.set_child(label)
            self.input_list.append(row)

        first = self.input_list.get_row_at_index(0)
        if first:
            self.input_list.select_row(first)

    def select_matching_tablet(self, device_name: str):
        if not self.tablets:
            return None
        lowered = device_name.lower()
        for t in self.tablets:
            if t.Name.lower() in lowered or t.Model.lower() in lowered:
                return t
        return self.tablets[0]

    def refresh_device_pages(self) -> None:
        self.refresh_pad_page()
        self.refresh_mapping_controls()
        self.refresh_pressure_page()

    def get_button_obj(self, callsign: str):
        if not self.current_tablet or not getattr(self.current_tablet, "Buttons", None):
            return None
        for b in self.current_tablet.Buttons:
            if b.Callsign == callsign:
                return b
        return None

    def get_wayland_mapping_for_button(self, button_obj) -> tuple[str, str]:
        if not self.current_tablet:
            return "ignore", "Ignore"
        idx = wayland_button_index(self.current_tablet.Model, button_obj.Callsign, button_obj.Number)
        if idx is None:
            return "ignore", "Ignore"
        cfg = load_wayland_config()
        action = cfg.get("mappings", {}).get(str(idx))
        if not action:
            return "ignore", "Ignore"
        label = action.get("label", "")
        if label in self.mouse_action_values:
            return "mouse", label
        return "key", label

    def refresh_pad_page(self) -> None:
        for _name, dropdown, _callsign, _idx in self._touchstrip_slots():
            dropdown.set_selected(0)

        if not self.current_device or not self.current_tablet:
            self.touchstrip_status.set_text("Select a pad device to edit touch strip actions.")
            self.touchstrip_apply_btn.set_sensitive(False)
            return

        self.touchstrip_apply_btn.set_sensitive(True)
        if self.backend.session_type == "wayland":
            cfg = load_wayland_config()
            strip_mappings = cfg.get("strip_mappings", {})
            mappings = cfg.get("mappings", {})
            legacy_idx = {
                "left_up": "4",
                "left_down": "5",
                "right_up": "6",
                "right_down": "7",
            }
            for _name, dropdown, _callsign, slot_key in self._touchstrip_slots():
                entry = strip_mappings.get(slot_key)
                if not entry:
                    entry = mappings.get(legacy_idx.get(slot_key, ""))
                label = entry.get("label", "Ignore") if entry else "Ignore"
                cmd = entry.get("command") if entry else None
                action = self._touchstrip_command_to_action(cmd, label)
                self._set_touchstrip_dropdown_value(dropdown, action)
            self.touchstrip_status.set_text("Loaded touch strip actions from Wayland mapping file.")
            return

        if not self.backend.use_xsetwacom:
            self.touchstrip_apply_btn.set_sensitive(False)
            self.touchstrip_status.set_text("Touch strip mapping requires xsetwacom on X11.")
            return

        for _name, dropdown, callsign, _idx_key in self._touchstrip_slots():
            action_type, action_name = self.backend.getTypeAndName(self.current_device.identifier, callsign)
            if action_type == 1 and action_name in self.touchstrip_action_values:
                self._set_touchstrip_dropdown_value(dropdown, action_name)
            elif action_type == 2 and action_name in ("PAGEUP", "PAGEDOWN"):
                self._set_touchstrip_dropdown_value(dropdown, "Page Up" if action_name == "PAGEUP" else "Page Down")
            else:
                self._set_touchstrip_dropdown_value(dropdown, "Ignore")
        self.touchstrip_status.set_text("Loaded touch strip actions from xsetwacom.")

    def on_touchstrip_apply(self, _button: Gtk.Button) -> None:
        if not self.current_device or not self.current_tablet:
            self.touchstrip_status.set_text("Select a pad device first.")
            return

        if self.backend.session_type == "wayland":
            cfg = load_wayland_config()
            cfg["pad_name_contains"] = self.current_device.name
            strip_mappings = cfg.setdefault("strip_mappings", {})
            mappings = cfg.setdefault("mappings", {})
            legacy_idx = {
                "left_up": "4",
                "left_down": "5",
                "right_up": "6",
                "right_down": "7",
            }

            for slot_name, dropdown, _callsign, slot_key in self._touchstrip_slots():
                selected = self._selected_index(dropdown)
                action = self.touchstrip_action_values[selected] if 0 <= selected < len(self.touchstrip_action_values) else "Ignore"
                if action == "Ignore":
                    strip_mappings.pop(slot_key, None)
                    mappings.pop(legacy_idx.get(slot_key, ""), None)
                    continue
                cmd = self._touchstrip_action_to_command(action)
                if not cmd:
                    self.touchstrip_status.set_text(f"{slot_name}: unsupported action '{action}'.")
                    return
                strip_mappings[slot_key] = {"label": action, "command": cmd}
                mappings.pop(legacy_idx.get(slot_key, ""), None)

            save_wayland_config(cfg)
            self.touchstrip_status.set_text("Touch strip mappings saved. Run wayland_pad_daemon.py.")
            return

        if not self.backend.use_xsetwacom:
            self.touchstrip_status.set_text("Touch strip mapping requires xsetwacom on X11.")
            return

        for slot_name, dropdown, callsign, _idx_key in self._touchstrip_slots():
            selected = self._selected_index(dropdown)
            action = self.touchstrip_action_values[selected] if 0 <= selected < len(self.touchstrip_action_values) else "Ignore"
            if action == "Ignore":
                ok = self.backend.setByTypeAndName(self.current_device.identifier, callsign, 0)
            elif action in self.mouse_action_values:
                ok = self.backend.setByTypeAndName(self.current_device.identifier, callsign, 1, action)
            elif action == "Page Up":
                ok = self.backend.setByTypeAndName(self.current_device.identifier, callsign, 2, "PAGEUP")
            elif action == "Page Down":
                ok = self.backend.setByTypeAndName(self.current_device.identifier, callsign, 2, "PAGEDOWN")
            else:
                self.touchstrip_status.set_text(f"{slot_name}: unsupported action '{action}'.")
                return
            if not ok:
                self.touchstrip_status.set_text(f"Failed to apply {slot_name}.")
                return

        self.touchstrip_status.set_text("Touch strip mappings applied.")

    def on_edit_button_clicked(self, _button: Gtk.Button, button_obj) -> None:
        device_id = self.current_device.identifier if self.current_device else None
        pad_name = self.current_device.name if self.current_device else "Wacom"
        tablet_model = self.current_tablet.Model if self.current_tablet else None
        dialog = ButtonMappingDialog(self.window, self.backend, device_id, pad_name, tablet_model, button_obj)

        def _refresh_on_close(_w):
            self.refresh_pad_page()
            self.refresh_mapping_controls()
            return False

        dialog.connect("close-request", _refresh_on_close)
        dialog.present()

    def update_pressure_availability(self) -> None:
        enabled = self.backend.use_xsetwacom
        self.devicemodecombo.set_sensitive(enabled)
        self.clickforce_scale.set_sensitive(enabled)
        self.cp1x.set_sensitive(enabled)
        self.cp1y.set_sensitive(enabled)
        self.cp2x.set_sensitive(enabled)
        self.cp2y.set_sensitive(enabled)
        self.apply_pressure_curve_btn.set_sensitive(enabled)
        if enabled:
            self.pressure_support.set_text("Pressure settings are applied via xsetwacom (X11).")
        else:
            self.pressure_support.set_text("Wayland does not support xsetwacom pressure controls directly.")

    def refresh_pressure_page(self) -> None:
        if not self.current_device or not self.backend.use_xsetwacom:
            return

        self._updating_pressure_ui = True
        try:
            mode = self.backend.get_mode(self.current_device.identifier)
            if mode in ("Absolute", "Relative"):
                self.devicemodecombo.set_selected(self.mode_values.index(mode))

            force = self.backend.get_click_force(self.current_device.identifier)
            if force is not None:
                self.clickforce_scale.set_value(max(0.0, min(100.0, force * (100.0 / 19.0))))

            curve = self.backend.get_pressure_curve(self.current_device.identifier)
            if curve and len(curve) == 4:
                self.cp1x.set_value(curve[0])
                self.cp1y.set_value(curve[1])
                self.cp2x.set_value(curve[2])
                self.cp2y.set_value(curve[3])
        finally:
            self._updating_pressure_ui = False

    def refresh_mapping_controls(self) -> None:
        self.map_button_values = []
        self._set_dropdown_items(self.map_button_combo, [])
        self.mapping_pad_widget.set_parameters(self.current_tablet)

        has_buttons = bool(self.current_tablet and getattr(self.current_tablet, "Buttons", None))
        wayland_mode = self.backend.session_type == "wayland"
        editable = has_buttons and (self.backend.use_xsetwacom or wayland_mode)
        self.map_button_combo.set_sensitive(editable)
        self.map_type_combo.set_sensitive(editable)
        self.mouse_action_combo.set_sensitive(editable)
        self.key_action_entry.set_sensitive(editable)
        self.apply_map_btn.set_sensitive(editable)

        if not has_buttons:
            self.mapping_pad_widget.set_selected_callsign(None)
            self.map_status.set_text("This device has no known pad button map.")
            return
        if not editable:
            self.mapping_pad_widget.set_selected_callsign(None)
            if wayland_mode:
                self.map_status.set_text("Wayland mapping requires ydotool backend.")
            else:
                self.map_status.set_text("Button mapping requires xsetwacom.")
            return

        for b in self.current_tablet.Buttons:
            self.map_button_values.append(b.Callsign)

        self._set_dropdown_items(
            self.map_button_combo,
            [f"{b.Name}" for b in self.current_tablet.Buttons],
        )

        if self.current_tablet.Buttons:
            self.map_button_combo.set_selected(0)
            self.sync_mapping_preview_selection(self.map_button_values[0])
            self.load_current_button_mapping(self.map_button_values[0])

    def sync_mapping_preview_selection(self, callsign: str | None) -> None:
        self.mapping_pad_widget.set_selected_callsign(callsign)

    def load_current_button_mapping(self, callsign: str) -> None:
        if not self.current_device:
            return
        if self.backend.session_type == "wayland":
            button_obj = self.get_button_obj(callsign)
            if not button_obj:
                return
            kind, action_name = self.get_wayland_mapping_for_button(button_obj)
            if kind == "ignore":
                self.map_type_combo.set_selected(0)
                self.key_action_entry.set_text("")
            elif kind == "mouse":
                self.map_type_combo.set_selected(1)
                if action_name in self.mouse_action_values:
                    self.mouse_action_combo.set_selected(self.mouse_action_values.index(action_name))
                self.key_action_entry.set_text("")
            else:
                self.map_type_combo.set_selected(2)
                self.key_action_entry.set_text(action_name)
            self.on_map_type_changed(self.map_type_combo)
            return

        action_type, action_name = self.backend.getTypeAndName(self.current_device.identifier, callsign)
        if action_type == 0:
            self.map_type_combo.set_selected(0)
            self.key_action_entry.set_text("")
        elif action_type == 1:
            self.map_type_combo.set_selected(1)
            for idx, label in enumerate(self.mouse_action_values):
                if label == action_name:
                    self.mouse_action_combo.set_selected(idx)
                    break
            self.key_action_entry.set_text("")
        else:
            self.map_type_combo.set_selected(2)
            self.key_action_entry.set_text(action_name)
        self.on_map_type_changed(self.map_type_combo)

    def update_wayland_buttons(self) -> None:
        enabled = self.backend.supports_sway_mapping()
        self.map_output_btn.set_sensitive(enabled)
        self.map_all_btn.set_sensitive(enabled)
        self.output_entry.set_sensitive(enabled)

    def maybe_save_command(self, command: list[str]) -> None:
        if not self.save_commands.get_active():
            return
        ensure_config_file()
        command_line = " ".join(f"'{part}'" if " " in part else part for part in command)
        with CONFIG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{command_line}\n")

    def on_select_device(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            self.current_device = None
            self.current_tablet = None
            return

        idx = row.get_index()
        if idx < 0 or idx >= len(self.devices):
            return

        self.current_device = self.devices[idx]
        self.current_tablet = self.select_matching_tablet(self.current_device.name)
        self.tablet_label.set_text(self.current_device.name)
        model_name = self.current_tablet.Model if self.current_tablet else "unknown"
        self.welcome_text.set_text(
            f"Selected: {self.current_device.identifier}\nDetected model: {model_name}"
        )
        self.refresh_device_pages()
        if "pad" in self.current_device.name.lower():
            self.stack.set_visible_child_name("touchstrip")

    def on_toggle_startup(self, button: Gtk.CheckButton) -> None:
        write_configure_on_login(button.get_active())

    def on_mode_changed(self, widget: Gtk.DropDown, _pspec=None) -> None:
        if self._updating_pressure_ui or not self.current_device or not self.backend.use_xsetwacom:
            return
        idx = self._selected_index(widget)
        mode = self.mode_values[idx] if 0 <= idx < len(self.mode_values) else ""
        if mode:
            self.backend.set_mode(self.current_device.identifier, mode)

    def on_click_force_changed(self, widget: Gtk.Scale) -> None:
        if self._updating_pressure_ui or not self.current_device or not self.backend.use_xsetwacom:
            return
        force = widget.get_value() * (19.0 / 100.0)
        self.backend.set_click_force(self.current_device.identifier, force)

    def on_apply_pressure_curve(self, _button: Gtk.Button) -> None:
        if not self.current_device or not self.backend.use_xsetwacom:
            return
        points = [
            self.cp1x.get_value(),
            self.cp1y.get_value(),
            self.cp2x.get_value(),
            self.cp2y.get_value(),
        ]
        self.backend.set_pressure_curve(self.current_device.identifier, points)

    def on_map_type_changed(self, widget: Gtk.DropDown, _pspec=None) -> None:
        idx = self._selected_index(widget)
        active = self.map_type_values[idx] if 0 <= idx < len(self.map_type_values) else "ignore"
        self.mouse_action_combo.set_sensitive(active == "mouse")
        self.key_action_entry.set_sensitive(active == "key")

    def on_map_button_changed(self, widget: Gtk.DropDown, _pspec=None) -> None:
        if self._map_syncing_selection:
            return
        idx = self._selected_index(widget)
        callsign = self.map_button_values[idx] if 0 <= idx < len(self.map_button_values) else None
        if callsign:
            self.sync_mapping_preview_selection(callsign)
            self.load_current_button_mapping(callsign)

    def on_mapping_preview_selected(self, button_obj) -> None:
        if not button_obj:
            return
        callsign = getattr(button_obj, "Callsign", None)
        if not callsign:
            return
        if callsign not in self.map_button_values:
            return
        idx = self.map_button_values.index(callsign)
        self._map_syncing_selection = True
        try:
            self.map_button_combo.set_selected(idx)
        finally:
            self._map_syncing_selection = False
        self.sync_mapping_preview_selection(callsign)
        self.load_current_button_mapping(callsign)

    def on_apply_map(self, _button: Gtk.Button) -> None:
        if not self.current_device:
            self.map_status.set_text("Select a device first.")
            return

        map_idx = self._selected_index(self.map_button_combo)
        callsign = self.map_button_values[map_idx] if 0 <= map_idx < len(self.map_button_values) else None
        if not callsign:
            self.map_status.set_text("Select a button first.")
            return

        type_idx = self._selected_index(self.map_type_combo)
        map_type = self.map_type_values[type_idx] if 0 <= type_idx < len(self.map_type_values) else "ignore"

        if self.backend.session_type == "wayland":
            button_obj = self.get_button_obj(callsign)
            if not button_obj or not self.current_tablet:
                self.map_status.set_text("Cannot resolve selected button.")
                return
            idx = wayland_button_index(self.current_tablet.Model, button_obj.Callsign, button_obj.Number)
            if idx is None:
                self.map_status.set_text("Unsupported button index mapping.")
                return
            cfg = load_wayland_config()
            cfg["pad_name_contains"] = self.current_device.name
            mappings = cfg.setdefault("mappings", {})
            key = str(idx)

            if map_type == "ignore":
                mappings.pop(key, None)
                save_wayland_config(cfg)
                self.map_status.set_text(f"Wayland mapping cleared for idx {idx}.")
                self.refresh_pad_page()
                return

            if map_type == "mouse":
                mouse_idx = self._selected_index(self.mouse_action_combo)
                label = self.mouse_action_values[mouse_idx] if 0 <= mouse_idx < len(self.mouse_action_values) else "Left Click"
                cmd = wayland_mouse_command(label)
                if not cmd:
                    self.map_status.set_text("Mouse action not supported in Wayland mapper.")
                    return
                mappings[key] = {"label": label, "command": cmd}
                save_wayland_config(cfg)
                self.map_status.set_text(f"Saved Wayland mapping for idx {idx}. Run wayland_pad_daemon.py.")
                self.refresh_pad_page()
                return

            keys = self.key_action_entry.get_text().strip()
            cmd = key_sequence_to_ydotool_command(keys)
            if not keys or not cmd:
                self.map_status.set_text("Invalid key sequence for ydotool conversion.")
                return
            mappings[key] = {"label": keys, "command": cmd}
            save_wayland_config(cfg)
            self.map_status.set_text(f"Saved Wayland mapping for idx {idx}. Run wayland_pad_daemon.py.")
            self.refresh_pad_page()
            return

        if not self.backend.use_xsetwacom:
            self.map_status.set_text("Button mapping requires xsetwacom.")
            return

        ok = False

        if map_type == "ignore":
            ok = self.backend.setByTypeAndName(self.current_device.identifier, callsign, 0)
        elif map_type == "mouse":
            mouse_idx = self._selected_index(self.mouse_action_combo)
            label = self.mouse_action_values[mouse_idx] if 0 <= mouse_idx < len(self.mouse_action_values) else "Left Click"
            ok = self.backend.setByTypeAndName(self.current_device.identifier, callsign, 1, label)
        else:
            keys = self.key_action_entry.get_text().strip()
            if not keys:
                self.map_status.set_text("Enter a key sequence.")
                return
            if not self.backend.verifyString(keys):
                self.map_status.set_text("Invalid key sequence for xsetwacom.")
                return
            ok = self.backend.setByTypeAndName(self.current_device.identifier, callsign, 2, keys)

        self.map_status.set_text("Button mapping updated." if ok else "Failed to update button mapping.")
        self.refresh_pad_page()

    def on_map_output(self, _button: Gtk.Button) -> None:
        if not self.current_device:
            self.welcome_text.set_text("Select a device first.")
            return
        output = self.output_entry.get_text().strip()
        if not output:
            self.welcome_text.set_text("Enter output name, e.g. HDMI-A-1")
            return
        ok, msg = self.backend.map_to_output(self.current_device.identifier, output)
        self.welcome_text.set_text(f"map_to_output: {msg}")
        if ok:
            self.maybe_save_command(self.backend.build_map_command(self.current_device.identifier, output))

    def on_map_all(self, _button: Gtk.Button) -> None:
        if not self.current_device:
            self.welcome_text.set_text("Select a device first.")
            return
        ok, msg = self.backend.map_to_all_outputs(self.current_device.identifier)
        self.welcome_text.set_text(f"map_to_all_outputs: {msg}")
        if ok:
            self.maybe_save_command(self.backend.build_map_command(self.current_device.identifier, "*"))

    def on_refresh(self, _button: Gtk.Button) -> None:
        self.refresh_devices()

    def on_help(self, _button: Gtk.Button) -> None:
        win = Gtk.Window(title="Wacom Help")
        win.set_transient_for(self.window)
        win.set_modal(True)
        win.set_default_size(860, 620)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(10)
        root.set_margin_bottom(10)
        root.set_margin_start(10)
        root.set_margin_end(10)
        win.set_child(root)

        title = Gtk.Label()
        title.set_markup("<b>Intuos3 Button Layout (from wacom.sh)</b>")
        title.set_xalign(0.0)
        root.append(title)

        tv = Gtk.TextView()
        tv.set_editable(False)
        tv.set_monospace(True)
        tv.set_wrap_mode(Gtk.WrapMode.NONE)
        tv.get_buffer().set_text(load_wacom_ascii_diagram())

        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_child(tv)
        root.append(scroll)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.END)
        root.append(row)

        doc_btn = Gtk.Button(label="Open LinuxWacom Docs")
        close_btn = Gtk.Button(label="Close")
        row.append(doc_btn)
        row.append(close_btn)

        doc_btn.connect("clicked", lambda _b: webbrowser.open("https://github.com/linuxwacom/wacom"))
        close_btn.connect("clicked", lambda _b: win.close())
        win.present()

    def on_close(self, _button: Gtk.Button) -> None:
        self.app.quit()

    def present(self) -> None:
        self.window.present()


class WacomUtilityApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.wacom.utility.gtk4.legacy")
        self.main_window: MainWindow | None = None

    def do_activate(self) -> None:
        if self.main_window is None:
            try:
                self.main_window = MainWindow(self)
            except Exception as exc:
                print(f"Failed to load GTK4 legacy UI: {exc}")
                self.quit()
                return
        self.main_window.present()


def main() -> int:
    if "--check" in sys.argv:
        backend = XSetWacom()
        print(f"session={backend.session_type}")
        print(f"backend={backend.describe_backend()}")
        print(f"devices={len(backend.list_devices())}")
        print(f"ui_exists={UI_PATH.exists()}")
        return 0

    if "--configure" in sys.argv or "-c" in sys.argv:
        return run_configure_mode()

    if not Gtk.init_check():
        print("GTK4 cannot be initialized in current environment (missing GUI display).")
        return 1

    app = WacomUtilityApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
