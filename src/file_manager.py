import gi
import os
import json
from datetime import datetime

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib

UI_FILE = "ui/file_manager.ui"
CONFIG_FILE = os.path.expanduser("~/.config/propad/file_history.json")


class FileHistory:
    """Manages file history with tags and metadata."""

    def __init__(self):
        self.history = self.load_history()

    def load_history(self):
        """Load file history from config."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")

        return {
            "files": {},  # filepath -> {last_opened, last_edited, created, opened_count, tags}
            "order": [],  # List of filepaths in order
        }

    def save_history(self):
        """Save file history to config."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_file(self, filepath, action="opened"):
        """Add or update file in history with action tag."""
        now = datetime.now().isoformat()

        if filepath not in self.history["files"]:
            # New file
            self.history["files"][filepath] = {
                "created": now if action == "created" else None,
                "last_opened": now if action == "opened" else None,
                "last_edited": now if action == "edited" else None,
                "opened_count": 1 if action == "opened" else 0,
                "tags": [action],
            }
        else:
            # Update existing file
            file_data = self.history["files"][filepath]

            if action == "opened":
                file_data["last_opened"] = now
                file_data["opened_count"] = file_data.get("opened_count", 0) + 1
            elif action == "edited":
                file_data["last_edited"] = now
            elif action == "created":
                if not file_data.get("created"):
                    file_data["created"] = now

            # Add tag if not present
            if action not in file_data.get("tags", []):
                if "tags" not in file_data:
                    file_data["tags"] = []
                file_data["tags"].append(action)

        # Update order
        if filepath in self.history["order"]:
            self.history["order"].remove(filepath)
        self.history["order"].insert(0, filepath)

        # Keep only last 50 files
        self.history["order"] = self.history["order"][:50]

        # Clean up files not in order
        files_to_remove = [
            f for f in self.history["files"] if f not in self.history["order"]
        ]
        for f in files_to_remove:
            del self.history["files"][f]

        self.save_history()

    def remove_file(self, filepath):
        """Remove file from history."""
        if filepath in self.history["files"]:
            del self.history["files"][filepath]
        if filepath in self.history["order"]:
            self.history["order"].remove(filepath)
        self.save_history()

    def clear_history(self):
        """Clear all history."""
        self.history = {"files": {}, "order": []}
        self.save_history()

    def get_files(self):
        """Get list of files in order with metadata."""
        result = []
        for filepath in self.history["order"]:
            if filepath in self.history["files"]:
                data = self.history["files"][filepath].copy()
                data["filepath"] = filepath
                result.append(data)
        return result


@Gtk.Template(filename=UI_FILE)
class FileManagerDialog(Adw.Window):
    __gtype_name__ = "FileManagerDialog"

    btn_new = Gtk.Template.Child()
    btn_open = Gtk.Template.Child()
    btn_save = Gtk.Template.Child()
    btn_save_as = Gtk.Template.Child()
    btn_close = Gtk.Template.Child()
    btn_clear_history = Gtk.Template.Child()
    entry_current_file = Gtk.Template.Child()
    listbox_recent = Gtk.Template.Child()

    def __init__(self, parent_window, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(parent_window)
        self.parent_window = parent_window

        self.current_file = None
        self.file_history = FileHistory()

        # Connect signals
        self.btn_new.connect("clicked", self._on_new_clicked)
        self.btn_open.connect("clicked", self._on_open_clicked)
        self.btn_save.connect("clicked", self._on_save_clicked)
        self.btn_save_as.connect("clicked", self._on_save_as_clicked)
        self.btn_close.connect("clicked", self._on_close_clicked)
        self.btn_clear_history.connect("clicked", self._on_clear_history)
        self.listbox_recent.connect("row-activated", self._on_recent_activated)

        self.populate_recent_files()

    def _on_clear_history(self, button):
        """Clear all file history."""
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading("Clear History?")
        dialog.set_body(
            "This will remove all file history. This action cannot be undone."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear History")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_clear_history_response)
        dialog.present()

    def _on_clear_history_response(self, dialog, response):
        """Handle clear history response."""
        if response == "clear":
            self.file_history.clear_history()
            self.populate_recent_files()

    def populate_recent_files(self):
        """Populate the recent files list with tags."""
        # Clear existing items
        while True:
            row = self.listbox_recent.get_row_at_index(0)
            if row is None:
                break
            self.listbox_recent.remove(row)

        # Add recent files
        files = self.file_history.get_files()
        for file_data in files:
            filepath = file_data["filepath"]

            # Check if file exists
            if not os.path.exists(filepath):
                continue

            row = Gtk.ListBoxRow()
            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            main_box.set_margin_start(8)
            main_box.set_margin_end(8)
            main_box.set_margin_top(8)
            main_box.set_margin_bottom(8)

            # Top box - icon, filename, and delete button
            top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

            icon = Gtk.Image.new_from_icon_name("document-open-symbolic")
            label = Gtk.Label(label=os.path.basename(filepath))
            label.set_xalign(0)
            label.set_hexpand(True)
            label.add_css_class("heading")

            # Delete button
            delete_btn = Gtk.Button()
            delete_btn.set_icon_name("user-trash-symbolic")
            delete_btn.add_css_class("flat")
            delete_btn.set_tooltip_text("Remove from history")
            delete_btn.filepath = filepath
            delete_btn.connect("clicked", self._on_delete_file_from_history)

            top_box.append(icon)
            top_box.append(label)
            top_box.append(delete_btn)

            # Path box
            path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            path_label = Gtk.Label(label=os.path.dirname(filepath))
            path_label.add_css_class("dim-label")
            path_label.set_xalign(0)
            path_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            path_box.append(path_label)

            # Tags box
            tags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            tags = file_data.get("tags", [])

            # Tag colors
            tag_colors = {"created": "success", "opened": "accent", "edited": "warning"}

            for tag in tags:
                tag_label = Gtk.Label(label=tag.capitalize())
                tag_label.add_css_class("pill")
                if tag in tag_colors:
                    tag_label.add_css_class(tag_colors[tag])
                tags_box.append(tag_label)

            # Opened count
            if file_data.get("opened_count", 0) > 0:
                count_label = Gtk.Label(label=f"Opened {file_data['opened_count']}x")
                count_label.add_css_class("dim-label")
                count_label.add_css_class("caption")
                tags_box.append(count_label)

            main_box.append(top_box)
            main_box.append(path_box)
            main_box.append(tags_box)

            row.set_child(main_box)
            row.filepath = filepath
            self.listbox_recent.append(row)

    def _on_delete_file_from_history(self, button):
        """Delete a single file from history."""
        filepath = button.filepath
        self.file_history.remove_file(filepath)
        self.populate_recent_files()

    def _on_new_clicked(self, button):
        """Create a new file."""
        if self.parent_window and self.parent_window.content_modified:
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Save Changes?",
                body="The document has unsaved changes. Do you want to save them?",
            )
            dialog.add_response("discard", "Discard")
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("save", "Save")
            dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_response_appearance(
                "discard", Adw.ResponseAppearance.DESTRUCTIVE
            )
            dialog.connect("response", self._on_new_save_response)
            dialog.present()
        else:
            self._create_new_file()

    def _on_new_save_response(self, dialog, response):
        """Handle save response for new file."""
        if response == "save":
            if self.current_file:
                self.save_file(self.current_file)
                self._create_new_file()
            else:
                self._on_save_as_clicked(None)
        elif response == "discard":
            self._create_new_file()

    def _create_new_file(self):
        """Create a new empty file."""
        if self.parent_window:
            sidebar = self.parent_window.get_sidebar()
            sidebar.clear()
            self.current_file = None
            self.parent_window.set_current_file(None)
            self.entry_current_file.set_text("Untitled.md")

    def _on_open_clicked(self, button):
        """Open file dialog."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Open Markdown File")

        filter_md = Gtk.FileFilter()
        filter_md.set_name("Markdown Files")
        filter_md.add_pattern("*.md")
        filter_md.add_pattern("*.markdown")
        filter_md.add_pattern("*.txt")

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All Files")
        filter_all.add_pattern("*")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_md)
        filters.append(filter_all)
        dialog.set_filters(filters)

        try:
            documents_path = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_DOCUMENTS
            )
            if documents_path and os.path.exists(documents_path):
                initial_folder = Gio.File.new_for_path(documents_path)
                dialog.set_initial_folder(initial_folder)
        except:
            pass

        dialog.open(self, None, self._on_open_response)

    def _on_open_response(self, dialog, result):
        """Handle file open response."""
        try:
            file = dialog.open_finish(result)
            if file:
                filepath = file.get_path()
                self.load_file(filepath, action="opened")
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"Error opening file: {e}")
                self._show_error_dialog("Open Error", f"Could not open file: {str(e)}")

    def load_file(self, filepath, action="opened"):
        """Load file content and track in history."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if self.parent_window:
                sidebar = self.parent_window.get_sidebar()
                sidebar.set_text(content)
                self.parent_window.set_current_file(filepath)

            self.current_file = filepath
            self.entry_current_file.set_text(filepath)

            # Add to history with action tag
            self.file_history.add_file(filepath, action)
            self.populate_recent_files()

            print(f"File loaded: {filepath}")

        except Exception as e:
            print(f"Error loading file: {e}")
            self._show_error_dialog("Load Error", f"Could not load file: {str(e)}")

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

        if self.current_file:
            initial_name = os.path.basename(self.current_file)
        else:
            initial_name = "untitled.md"

        dialog.set_initial_name(initial_name)

        try:
            if self.current_file:
                folder_path = os.path.dirname(self.current_file)
            else:
                folder_path = GLib.get_user_special_dir(
                    GLib.UserDirectory.DIRECTORY_DOCUMENTS
                )

            if folder_path and os.path.exists(folder_path):
                initial_folder = Gio.File.new_for_path(folder_path)
                dialog.set_initial_folder(initial_folder)
        except:
            pass

        dialog.save(self, None, self._on_save_as_response)

    def _on_save_as_response(self, dialog, result):
        """Handle save as response."""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()

                if not filepath.endswith((".md", ".markdown", ".txt")):
                    filepath += ".md"

                # Check if this is a new file
                is_new = not os.path.exists(filepath)

                self.save_file(filepath, is_new=is_new)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"Error saving file: {e}")
                self._show_error_dialog("Save Error", f"Could not save file: {str(e)}")

    def save_file(self, filepath, is_new=False):
        """Save file content and track in history."""
        try:
            if self.parent_window:
                sidebar = self.parent_window.get_sidebar()
                content = sidebar.get_text()

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

                self.current_file = filepath
                self.parent_window.set_current_file(filepath)
                self.parent_window.mark_content_modified(False)
                self.entry_current_file.set_text(filepath)

                # Add to history with appropriate action
                action = "created" if is_new else "edited"
                self.file_history.add_file(filepath, action)
                self.populate_recent_files()

                print(f"File saved: {filepath}")
                self._show_toast(f"Saved: {os.path.basename(filepath)}")

        except Exception as e:
            print(f"Error saving file: {e}")
            self._show_error_dialog("Save Error", f"Could not save file: {str(e)}")

    def _on_recent_activated(self, listbox, row):
        """Handle recent file activation."""
        if hasattr(row, "filepath"):
            self.load_file(row.filepath, action="opened")

    def _on_close_clicked(self, button):
        """Close dialog."""
        self.close()

    def _show_error_dialog(self, heading, body):
        """Show error dialog."""
        dialog = Adw.MessageDialog(transient_for=self, heading=heading, body=body)
        dialog.add_response("ok", "OK")
        dialog.present()

    def _show_toast(self, message):
        """Show a toast notification."""
        print(f"Toast: {message}")

    def get_current_file(self):
        """Get current file path."""
        return self.current_file