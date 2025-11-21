# -*- coding: utf-8 -*-
"""Python - PyGObject - GTK."""

import gi
import sys

gi.require_version(namespace="Gtk", version="4.0")
gi.require_version(namespace="Adw", version="1")

from gi.repository import Adw, Gio, Gtk
from window import Window

Adw.init()


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.propad.com", flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )

        self.create_action("quit", self.exit_app, ["<primary>q"])
        self.create_action("toggle-sidebar", self.toggle_sidebar, ["<primary>b"])

    def do_activate(self):
        win = self.props.active_window

        if not win:
            win = Window(application=self)

        win.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def exit_app(self, action, param):
        """Quit the application."""
        self.quit()

    def toggle_sidebar(self, action, param):
        """Toggle sidebar visibility."""
        win = self.props.active_window
        if win:
            overlay = win.adw_overlay_split_view
            overlay.set_show_sidebar(not overlay.get_show_sidebar())

    def create_action(self, name, callback, shortcuts=None):
        """Create an application action."""
        action = Gio.SimpleAction.new(name=name, parameter_type=None)
        action.connect("activate", callback)
        self.add_action(action=action)
        if shortcuts:
            self.set_accels_for_action(
                detailed_action_name=f"app.{name}",
                accels=shortcuts,
            )


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
