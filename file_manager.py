import gi
import os
import json

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib

UI_FILE = "ui/file_manager.ui"
CONFIG_FILE = os.path.expanduser("~/.config/propad/config.json")


@Gtk.Template(filename=UI_FILE)
class FileManagerDialog(Adw.Window):
    __gtype_name__ = "FileManagerDialog"

    btn_new = Gtk.Template.Child()
    btn_open = Gtk.Template.Child()
    btn_save = Gtk.Template.Child()
    btn_save_as = Gtk.Template.Child()
    btn_close = Gtk.Template.Child()
    entry_current_file = Gtk.Template.Child()
    listbox_recent = Gtk.Template.Child()

    def __init__(self, parent_window, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(parent_window)
        self.parent_window = parent_window

        self.current_file = None
        self.recent_files = self.load_recent_files()

        # Connect signals
        self.btn_new.connect("clicked", self._on_new_clicked)
        self.btn_open.connect("clicked", self._on_open_clicked)
        self.btn_save.connect("clicked", self._on_save_clicked)
        self.btn_save_as.connect("clicked", self._on_save_as_clicked)
        self.btn_close.connect("clicked", self._on_close_clicked)
        self.listbox_recent.connect("row-activated", self._on_recent_activated)

        self.populate_recent_files()

    def load_recent_files(self):
        """Load recent files from config."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    return config.get("recent_files", [])
        except Exception as e:
            print(f"Error loading recent files: {e}")
        return []

    def save_recent_files(self):
        """Save recent files to config."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            config = {"recent_files": self.recent_files}
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving recent files: {e}")

    def add_to_recent(self, filepath):
        """Add file to recent files list."""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath)
        self.recent_files = self.recent_files[:10]  # Keep only 10 recent
        self.save_recent_files()
        self.populate_recent_files()

    def populate_recent_files(self):
        """Populate the recent files list."""
        # Clear existing items
        while True:
            row = self.listbox_recent.get_row_at_index(0)
            if row is None:
                break
            self.listbox_recent.remove(row)

        # Add recent files
        for filepath in self.recent_files:
            if os.path.exists(filepath):
                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                box.set_margin_start(8)
                box.set_margin_end(8)
                box.set_margin_top(8)
                box.set_margin_bottom(8)

                icon = Gtk.Image.new_from_icon_name("document-open-symbolic")
                label = Gtk.Label(label=os.path.basename(filepath))
                label.set_xalign(0)
                label.set_hexpand(True)

                path_label = Gtk.Label(label=os.path.dirname(filepath))
                path_label.add_css_class("dim-label")
                path_label.set_xalign(1)

                box.append(icon)
                box.append(label)
                box.append(path_label)
                row.set_child(box)
                row.filepath = filepath
                self.listbox_recent.append(row)

    def _on_new_clicked(self, button):
        """Create a new file."""
        # Ask to save current file if modified
        if self.parent_window:
            sidebar = self.parent_window.get_sidebar()
            sidebar.clear()
            self.current_file = None
            self.entry_current_file.set_text("Untitled.md")

    def _on_open_clicked(self, button):
        """Open file dialog."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Open Markdown File")

        # Create file filter for markdown
        filter_md = Gtk.FileFilter()
        filter_md.set_name("Markdown Files")
        filter_md.add_pattern("*.md")
        filter_md.add_pattern("*.markdown")

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All Files")
        filter_all.add_pattern("*")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_md)
        filters.append(filter_all)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_open_response)

    def _on_open_response(self, dialog, result):
        """Handle file open response."""
        try:
            file = dialog.open_finish(result)
            if file:
                filepath = file.get_path()
                self.load_file(filepath)
        except Exception as e:
            print(f"Error opening file: {e}")

    def load_file(self, filepath):
        """Load file content."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if self.parent_window:
                sidebar = self.parent_window.get_sidebar()
                sidebar.set_text(content)

            self.current_file = filepath
            self.entry_current_file.set_text(filepath)
            self.add_to_recent(filepath)

        except Exception as e:
            print(f"Error loading file: {e}")

    def _on_save_clicked(self, button):
        """Save current file."""
        if self.current_file:
            self.save_file(self.current_file)
        else:
            self._on_save_as_clicked(button)

    def _on_save_as_clicked(self, button):
        """Save as dialog."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Markdown File")
        dialog.set_initial_name("untitled.md")

        dialog.save(self, None, self._on_save_as_response)

    def _on_save_as_response(self, dialog, result):
        """Handle save as response."""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()
                self.save_file(filepath)
        except Exception as e:
            print(f"Error saving file: {e}")

    def save_file(self, filepath):
        """Save file content."""
        try:
            if self.parent_window:
                sidebar = self.parent_window.get_sidebar()
                content = sidebar.get_text()

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

                self.current_file = filepath
                self.entry_current_file.set_text(filepath)
                self.add_to_recent(filepath)

                print(f"File saved: {filepath}")
        except Exception as e:
            print(f"Error saving file: {e}")

    def _on_recent_activated(self, listbox, row):
        """Handle recent file activation."""
        if hasattr(row, "filepath"):
            self.load_file(row.filepath)

    def _on_close_clicked(self, button):
        """Close dialog."""
        self.close()

    def get_current_file(self):
        """Get current file path."""
        return self.current_file
