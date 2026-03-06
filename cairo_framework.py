# Some cairo magic, thanks goes to Michael Urman for tutorials

import os
import cairo
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class DrawingArea(Gtk.DrawingArea):

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        # Keep a sensible minimum so previews are visible when expanded.
        self.set_content_width(360)
        self.set_content_height(260)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_draw_func(self.on_draw)

    def on_draw(self, _widget, cr, width, height):
        self.draw(cr, width, height)


class Pad(DrawingArea):
    def __init__(self):
        super().__init__()
        self.tablet = None
        self.button_map = []
        self.image = ""
        self.selected_callsign = None
        self._select_callback = None

        click = Gtk.GestureClick.new()
        click.connect("pressed", self.on_click_pressed)
        self.add_controller(click)

    def set_select_callback(self, callback):
        self._select_callback = callback

    def set_selected_callsign(self, callsign):
        self.selected_callsign = callsign
        self.queue_draw()

    def set_parameters(self, tablet=None):
        base_dir = Path(os.environ.get("WACOM_UTILITY_DATA_DIR", Path(__file__).resolve().parent))
        self.tablet = tablet
        self.selected_callsign = None
        if self.tablet:
            self.button_map = self.tablet.Buttons
            self.image = str(base_dir / "images" / "pad" / f"{self.tablet.Model}.png")
            try:
                os.stat(self.image)
            except:
                print("No image for %s pad" % self.tablet.Model)
                self.image = ""

        else:
            self.button_map = []
            self.image = ""
        self.queue_draw()

    def on_click_pressed(self, _gesture, _n_press, x, y):
        if not self.button_map:
            return
        for button in self.button_map:
            if button.X1 <= x <= button.X2 and button.Y1 <= y <= button.Y2:
                self.selected_callsign = button.Callsign
                self.queue_draw()
                if self._select_callback:
                    self._select_callback(button)
                return

    def draw(self, cr, width, height):
        cr.set_source_rgb(0.5, 0.5, 0.5)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        if self.image:
            # Draw background image
            cr.set_source_surface(
                cairo.ImageSurface.create_from_png(self.image))
            cr.paint()

        if self.button_map:
            # Paint on buttons
            cr.select_font_face(
                "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(18)

            for button in self.button_map:
                cr.set_source_rgba(1, 1, 1, 1)
                choffset = len(str(button.Number)) * 6
                cr.move_to(int((button.X1+button.X2)/2)-choffset,
                           int((button.Y1+button.Y2)/2)+6)
                cr.show_text(str(button.Number))
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.4)
                cr.rectangle(button.X1, button.Y1, button.X2 -
                             button.X1, button.Y2-button.Y1)
                cr.stroke()
                if self.selected_callsign == button.Callsign:
                    cr.set_source_rgba(1.0, 0.3, 0.2, 0.95)
                    cr.set_line_width(3.0)
                    cr.rectangle(button.X1, button.Y1, button.X2 - button.X1, button.Y2 - button.Y1)
                    cr.stroke()
                    cr.set_line_width(1.0)
        else:
            cr.select_font_face(
                "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(10)
            cr.set_source_rgba(1, 1, 1, 1)
            cr.move_to(0, 16)
            cr.show_text("No preview available for this model.")
