############################################################################
##
# Copyright (C) 2007 Alexander Macdonald. All rights reserved.
##
# Modified by QB89Dragon 2009 for inclusion to pen tablet utility
##
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License version 2
##
# Graphics Tablet Applet
##
############################################################################

import math
import subprocess
import cairo
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GObject


def GetPressCurve(devicename):
    command = ["xsetwacom", "get", devicename, "PressureCurve"]
    result = subprocess.run(command, capture_output=True, text=True)
    bits = result.stdout.strip().split()
    return [float(x) for x in bits]


def SetPressCurve(devicename, points):
    command = ["xsetwacom", "set", devicename, "PressureCurve", str(
        points[0]), str(points[1]), str(points[2]), str(points[3])]
    subprocess.run(command)


def GetClickForce(devicename):
    command = ["xsetwacom", "get", devicename, "Threshold"]
    result = subprocess.run(command, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0.0


def SetClickForce(devicename, force):
    command = ["xsetwacom", "set", devicename, "Threshold", str(force)]
    subprocess.run(command)


def GetMode(devicename):
    command = ["xsetwacom", "get", devicename, "Mode"]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip()


def SetMode(devicename, m):
    command = ["xsetwacom", "set", devicename, "Mode", str(m)]
    subprocess.run(command)


class PressureCurveWidget(Gtk.DrawingArea):
    def __init__(self):
        Gtk.DrawingArea.__init__(self)

        self.Points = [0, 100, 100, 0]
        self.Pressure = 0.0

        self.Radius = 5.0
        self.ControlPointStroke = 2.0
        self.ControlPointDiameter = (self.Radius * 2) + self.ControlPointStroke
        self.WindowSize = None
        self.Scale = None

        self.ClickForce = None
        self.DeviceName = ""

        self.DraggingCP1 = False
        self.DraggingCP2 = False

        self.set_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)

        self.connect("configure-event", self.ConfigureEvent)
        self.connect("draw", self.ExposeEvent)
        self.connect("motion-notify-event", self.MotionEvent)
        self.connect("button-press-event", self.ButtonPress)
        self.connect("button-release-event", self.ButtonRelease)
        self.set_size_request(100, 100)

    def SetDevice(self, name):
        self.DeviceName = name
        self.ClickForce = GetClickForce(name)

        if self.ClickForce:
            self.ClickForce *= (100.0 / 19.0)

        points = GetPressCurve(name)
        if not points:
            self.Points = None
        else:
            self.Points = [points[0], 100.0 -
                           points[1], points[2], 100.0 - points[3]]

    def Update(self):
        self.queue_draw()

    def ClampValue(self, v):
        if v < 0.0:
            return 0.0
        elif v > 100.0:
            return 100.0
        else:
            return v

    def ConfigureEvent(self, widget, event):
        self.WindowSize = widget.get_allocated_width(), widget.get_allocated_height()
        self.Scale = ((self.WindowSize[0] - self.ControlPointDiameter) / 100.0,
                      (self.WindowSize[1] - self.ControlPointDiameter) / 100.0)

    def MotionEvent(self, widget, event):
        if not self.Points:
            return
        pos = (event.x / self.Scale[0], event.y / self.Scale[1])

        if self.DraggingCP1:
            self.Points[0] = self.ClampValue(pos[0])
            self.Points[1] = self.ClampValue(pos[1])
            SetPressCurve(self.DeviceName, self.Points)
            self.Update()
        elif self.DraggingCP2:
            self.Points[2] = self.ClampValue(pos[0])
            self.Points[3] = self.ClampValue(pos[1])
            SetPressCurve(self.DeviceName, self.Points)
            self.Update()

    def ButtonPress(self, widget, event):
        if not self.Points:
            return
        pos = (event.x / self.Scale[0], event.y / self.Scale[1])

        if abs(pos[0] - self.Points[0]) < 10 and abs(pos[1] - self.Points[1]) < 10:
            self.DraggingCP1 = True
        elif abs(pos[0] - self.Points[2]) < 10 and abs(pos[1] - self.Points[3]) < 10:
            self.DraggingCP2 = True

    def ButtonRelease(self, widget, event):
        self.DraggingCP1 = False
        self.DraggingCP2 = False

    def ExposeEvent(self, widget, context):
        if not self.Points:
            context.set_source_rgb(0.5, 0.5, 0.5)
            context.paint()
            return

        context.set_source_rgb(1.0, 1.0, 1.0)
        context.paint()

        # Draw grid
        context.set_source_rgb(0.8, 0.8, 0.8)
        context.set_line_width(1.0)
        for i in range(0, 11):
            x = i * (self.WindowSize[0] / 10.0)
            y = i * (self.WindowSize[1] / 10.0)
            context.move_to(x, 0)
            context.line_to(x, self.WindowSize[1])
            context.move_to(0, y)
            context.line_to(self.WindowSize[0], y)
        context.stroke()

        # Draw curve
        context.set_source_rgb(0.0, 0.0, 0.0)
        context.set_line_width(2.0)
        context.move_to(self.Points[0] * self.Scale[0] + self.Radius,
                        self.Points[1] * self.Scale[1] + self.Radius)
        context.line_to(self.Points[2] * self.Scale[0] + self.Radius,
                        self.Points[3] * self.Scale[1] + self.Radius)
        context.stroke()

        # Draw control points
        context.set_source_rgb(1.0, 0.0, 0.0)
        context.arc(self.Points[0] * self.Scale[0] + self.Radius,
                    self.Points[1] * self.Scale[1] + self.Radius,
                    self.Radius, 0, 2 * math.pi)
        context.fill()

        context.arc(self.Points[2] * self.Scale[0] + self.Radius,
                    self.Points[3] * self.Scale[1] + self.Radius,
                    self.Radius, 0, 2 * math.pi)
        context.fill()


class DrawingTestWidget(Gtk.DrawingArea):
    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.Pressure = 0.0
        self.set_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect("motion-notify-event", self.MotionEvent)
        self.connect("button-press-event", self.ButtonPress)
        self.connect("button-release-event", self.ButtonRelease)
        self.connect("draw", self.ExposeEvent)

    def GetPressure(self):
        return self.Pressure

    def MotionEvent(self, widget, event):
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            self.Pressure = event.get_axis(Gdk.AxisUse.PRESSURE) if event.get_axis(
                Gdk.AxisUse.PRESSURE) else 0.0
            self.queue_draw()

    def ButtonPress(self, widget, event):
        pass

    def ButtonRelease(self, widget, event):
        pass

    def ExposeEvent(self, widget, context):
        context.set_source_rgb(1.0, 1.0, 1.0)
        context.paint()

        # Draw pressure indicator
        context.set_source_rgb(0.0, 0.0, 0.0)
        context.set_line_width(2.0)
        context.arc(50, 50, max(self.Pressure * 50, 5), 0, 2 * math.pi)
        context.stroke()


class GraphicsTabletApplet:
    def __init__(self, window, wTree, Device):
        self.Device = Device
        self.wTree = wTree
        self.MainWindow = window

        # Pressure Curve
        self.PressureCurveBox = wTree.get_object("PressureCurveBox")
        if self.PressureCurveBox:
            self.PressureWidget = PressureCurveWidget()
            self.PressureCurveBox.pack_start(
                self.PressureWidget, True, True, 0)
            self.PressureWidget.show()
            self.PressureWidget.SetDevice(self.Device)

        # Drawing test
        self.DrawingBox = wTree.get_object("DrawingBox")
        if self.DrawingBox:
            self.DrawingWidget = DrawingTestWidget()
            self.DrawingBox.pack_start(self.DrawingWidget, True, True, 0)
            self.DrawingWidget.show()

        # Click force slider
        self.ClickForceScale = wTree.get_object("ClickForceScale")
        if self.ClickForceScale:
            self.ClickForceScale.set_range(0.0, 100.0)
            force = GetClickForce(self.Device)
            if force:
                self.ClickForceScale.set_value(force * (100.0 / 19.0))
            self.ClickForceScale.connect(
                "value-changed", self.ClickForceChanged)

    def ClickForceChanged(self, widget):
        force = widget.get_value() * (19.0 / 100.0)
        SetClickForce(self.Device, force)
