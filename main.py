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
        self.window = None

    def do_activate(self):
        """Called when the application is activated."""
        if not self.window:
            self.window = Window(application=self)
        self.window.present()

    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)

        # Setup keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Setup application-wide keyboard shortcuts."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *args: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Ctrl>Q"])

        # File operations (window-level actions)
        self.set_accels_for_action("win.new-file", ["<Ctrl>N"])
        self.set_accels_for_action("win.open-file", ["<Ctrl>O"])
        self.set_accels_for_action("win.save-file", ["<Ctrl>S"])
        self.set_accels_for_action("win.save-as", ["<Ctrl><Shift>S"])

        self.set_accels_for_action("win.toggle-sync-scroll", ["<Ctrl><Alt>S"])

        self.set_accels_for_action("app.quit", ["<Ctrl>Q"])
        self.set_accels_for_action("app.about", ["F1"])

        # File Manager action - delegates to window
        file_manager_action = Gio.SimpleAction.new("file-manager", None)
        file_manager_action.connect("activate", self._on_file_manager)
        self.add_action(file_manager_action)
        self.set_accels_for_action("app.file-manager", ["<Ctrl><Shift>F"])

        # Export action - delegates to window
        export_action = Gio.SimpleAction.new("export", None)
        export_action.connect("activate", self._on_export)
        self.add_action(export_action)
        self.set_accels_for_action("app.export", ["<Ctrl><Shift>E"])

        # Find action - delegates to window
        find_action = Gio.SimpleAction.new("find", None)
        find_action.connect("activate", self._on_find)
        self.add_action(find_action)
        self.set_accels_for_action("app.find", ["<Ctrl>F"])

        # Replace action - delegates to window
        replace_action = Gio.SimpleAction.new("replace", None)
        replace_action.connect("activate", self._on_replace)
        self.add_action(replace_action)
        self.set_accels_for_action("app.replace", ["<Ctrl>H"])

        # About action - delegates to window
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def _on_file_manager(self, action, param):
        """Handle file manager action."""
        if self.window:
            self.window._on_file_manager_activate(action, param)

    def _on_export(self, action, param):
        """Handle export action."""
        if self.window:
            self.window._on_export_activate(action, param)

    def _on_find(self, action, param):
        """Handle find action."""
        if self.window:
            self.window.sidebar_widget.search_bar.show_search()

    def _on_replace(self, action, param):
        """Handle replace action."""
        if self.window:
            self.window.sidebar_widget.search_bar.show_replace()

    def _on_about(self, action, param):
        """Handle about action."""
        if self.window:
            self.window._on_about_activate(action, param)


def main():
    """Main entry point."""
    app = PropadApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
