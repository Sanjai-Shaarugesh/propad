# -*- coding: utf-8 -*-
"""Python - PyGObject - GTK."""

import gi
import sys

gi.require_version(namespace="Gtk", version="4.0")
gi.require_version(namespace="Adw", version="1")

from gi.repository import Adw, Gio, Gtk

UI_FILE = "ui/window.ui"


Adw.init()


@Gtk.Template(filename=UI_FILE)
class Window(Adw.ApplicationWindow):
    __gtype_name__ = "Window"

    toggle_sidebar_btn = Gtk.Template.Child()
    adw_overlay_split_view = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.toggle_sidebar_btn.connect(
            "clicked",
            lambda b: self.adw_overlay_split_view.set_show_sidebar(
                not self.adw_overlay_split_view.get_show_sidebar()
            ),
        )


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.propad.com", flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )

        self.create_action("quite", self.exit_app, ["<primary>q"])

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
        self.quit()

    def create_action(self, name, callback, shortcuts=None):
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
