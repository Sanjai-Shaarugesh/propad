#!/usr/bin/env python3

import gi
import sys

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio
from window import Window


class PropadApplication(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="com.example.propad",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self):
        """Called when the application is activated."""
        win = self.props.active_window
        if not win:
            win = Window(application=self)
        win.present()

    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)

        # Setup keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Setup application-wide keyboard shortcuts."""
        # Ctrl+Q: Quit
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *args: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Ctrl>Q"])

        # Ctrl+Shift+F: File Manager
        self.set_accels_for_action("app.file-manager", ["<Ctrl><Shift>F"])

        # Ctrl+Shift+E: Export
        self.set_accels_for_action("app.export", ["<Ctrl><Shift>E"])

        # Ctrl+F: Find
        self.set_accels_for_action("app.find", ["<Ctrl>F"])

        # Ctrl+H: Replace
        self.set_accels_for_action("app.replace", ["<Ctrl>H"])


def main():
    """Main entry point."""
    app = PropadApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
