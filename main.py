#!/usr/bin/env python3
# main.py - Complete with multi-window support, shortcuts window, and i18n

import gi
import sys
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib


from propad.i18n import init_locale, _

init_locale()


from propad.window import Window
from propad.shortcuts_window import ShortcutsWindow


class PropadApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.sanjai.PropPad",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
            | Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.windows = []

    def do_activate(self):
        if not self.windows:
            self._open_new_window()
        else:
            if self.windows:
                self.windows[-1].present()

    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)
        self._setup_shortcuts()
        self._setup_menu()

    def do_open(self, files, n_files, hint):
        for file in files:
            filepath = file.get_path()
            if filepath and os.path.exists(filepath):
                window = self._find_window_with_file(filepath)
                if window:
                    window.present()
                else:
                    self._open_new_window(filepath)
            else:
                None

        if not self.windows:
            self.do_activate()

    def do_command_line(self, command_line):
        """Handle command-line arguments."""
        options = command_line.get_arguments()[1:]  # skip program name

        files_to_open = []
        for arg in options:
            if arg.startswith("--") or arg.startswith("-"):
                if arg in ["--new-window", "-n"]:
                    self._open_new_window()
                    continue
            else:
                if os.path.exists(arg):
                    files_to_open.append(arg)
                else:
                    None

        if files_to_open:
            for filepath in files_to_open:
                window = self._find_window_with_file(filepath)
                if window:
                    window.present()
                else:
                    self._open_new_window(filepath)
        else:
            if not self.windows:
                self._open_new_window()
            else:
                self.do_activate()

        self.activate()
        return 0

    def _find_window_with_file(self, filepath):
        """Find if a window already has this file open."""
        for window in self.windows:
            if window.current_file == filepath:
                return window
        return None

    def _open_new_window(self, filepath=None):
        """Open a new application window."""
        window = Window(application=self)

        # Load file if specified
        if filepath:
            window.load_file(filepath)

        window.present()
        self.windows.append(window)

        # Remove window from list when closed
        window.connect("close-request", lambda w: self._on_window_closed(w))

    def _on_window_closed(self, window):
        """Handle window close event."""
        if window in self.windows:
            self.windows.remove(window)

        return False

    def _setup_menu(self):
        """Setup application menu."""
        # This can be used for menubar if needed
        pass

    def _setup_shortcuts(self):
        """Setup application-wide keyboard shortcuts."""
        # Quit action (closes all windows)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *args: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Ctrl>Q"])

        # New window action
        new_window_action = Gio.SimpleAction.new("new-window", None)
        new_window_action.connect("activate", lambda *args: self._open_new_window())
        self.add_action(new_window_action)
        self.set_accels_for_action("app.new-window", ["<Ctrl><Shift>N"])

        # File operations (window-level actions)
        self.set_accels_for_action("win.new-file", ["<Ctrl>N"])
        self.set_accels_for_action("win.open-file", ["<Ctrl>O"])
        self.set_accels_for_action("win.save-file", ["<Ctrl>S"])
        self.set_accels_for_action("win.save-as", ["<Ctrl><Shift>S"])
        self.set_accels_for_action("win.toggle-sync-scroll", ["<Ctrl><Alt>S"])

        # File Manager action
        file_manager_action = Gio.SimpleAction.new("file-manager", None)
        file_manager_action.connect("activate", self._on_file_manager)
        self.add_action(file_manager_action)
        self.set_accels_for_action("app.file-manager", ["<Ctrl><Shift>F"])

        # Export action
        export_action = Gio.SimpleAction.new("export", None)
        export_action.connect("activate", self._on_export)
        self.add_action(export_action)
        self.set_accels_for_action("app.export", ["<Ctrl><Shift>E"])

        # Find action
        find_action = Gio.SimpleAction.new("find", None)
        find_action.connect("activate", self._on_find)
        self.add_action(find_action)
        self.set_accels_for_action("app.find", ["<Ctrl>F"])

        # Replace action
        replace_action = Gio.SimpleAction.new("replace", None)
        replace_action.connect("activate", self._on_replace)
        self.add_action(replace_action)
        self.set_accels_for_action("app.replace", ["<Ctrl>H"])

        # Shortcuts window action
        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self._on_shortcuts)
        self.add_action(shortcuts_action)
        self.set_accels_for_action(
            "app.shortcuts", ["<Ctrl>question", "<Ctrl><Shift>slash"]
        )

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)
        self.set_accels_for_action("app.about", ["F1"])

    def _get_active_window(self):
        """Get the currently active window."""
        active = self.get_active_window()
        if active and isinstance(active, Window):
            return active
        elif self.windows:
            return self.windows[-1]
        return None

    def _on_file_manager(self, action, param):
        """Handle file manager action."""
        window = self._get_active_window()
        if window:
            window._on_file_manager_activate(action, param)

    def _on_export(self, action, param):
        """Handle export action."""
        window = self._get_active_window()
        if window:
            window._on_export_activate(action, param)

    def _on_find(self, action, param):
        """Handle find action."""
        window = self._get_active_window()
        if window:
            window.sidebar_widget.search_bar.show_search()

    def _on_replace(self, action, param):
        """Handle replace action."""
        window = self._get_active_window()
        if window:
            window.sidebar_widget.search_bar.show_replace()

    def _on_shortcuts(self, action, param):
        """Show the shortcuts window."""
        window = self._get_active_window()
        if window:
            shortcuts_window = ShortcutsWindow(parent=window)
            shortcuts_window.present()

    def _on_about(self, action, param):
        """Handle about action."""
        window = self._get_active_window()
        if window:
            window._on_about_activate(action, param)


def main():
    """Main entry point."""
    Adw.init()
    app = PropadApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
