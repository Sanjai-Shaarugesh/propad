import gi
import json
import os

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

CONFIG_DIR = os.path.expanduser("~/.config/propad")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")


class StateManager:
    """Manages application state persistence."""

    def __init__(self):
        self.state = self.load_state()

    def load_state(self):
        """Load application state from file."""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")

        return {
            "window": {"width": 950, "height": 750, "maximized": False},
            "current_file": None,
            "content": "",
            "cursor_position": 0,
            "sidebar_visible": True,
            "webview_hidden": False,
        }

    def save_state(self):
        """Save application state to file."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(STATE_FILE, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")

    def get_window_state(self):
        """Get window state."""
        return self.state.get("window", {})

    def save_window_state(self, window):
        """Save window state."""
        self.state["window"] = {
            "width": window.get_default_size()[0],
            "height": window.get_default_size()[1],
            "maximized": window.is_maximized(),
        }
        self.save_state()

    def get_content(self):
        """Get saved content."""
        return self.state.get("content", "")

    def save_content(self, content):
        """Save content."""
        self.state["content"] = content
        self.save_state()

    def get_cursor_position(self):
        """Get saved cursor position."""
        return self.state.get("cursor_position", 0)

    def save_cursor_position(self, position):
        """Save cursor position."""
        self.state["cursor_position"] = position
        self.save_state()

    def get_current_file(self):
        """Get current file path."""
        return self.state.get("current_file")

    def save_current_file(self, filepath):
        """Save current file path."""
        self.state["current_file"] = filepath
        self.save_state()

    def is_sidebar_visible(self):
        """Check if sidebar is visible."""
        return self.state.get("sidebar_visible", True)

    def save_sidebar_visible(self, visible):
        """Save sidebar visibility."""
        self.state["sidebar_visible"] = visible
        self.save_state()

    def is_webview_hidden(self):
        """Check if webview is hidden."""
        return self.state.get("webview_hidden", False)

    def save_webview_hidden(self, hidden):
        """Save webview hidden state."""
        self.state["webview_hidden"] = hidden
        self.save_state()

    def save_all(self, window, sidebar, webview_hidden):
        """Save all state at once."""
        # Window state
        width, height = window.get_default_size()
        self.state["window"] = {
            "width": width,
            "height": height,
            "maximized": window.is_maximized(),
        }

        # Content and cursor
        buffer = sidebar.buffer
        self.state["content"] = sidebar.get_text()
        cursor = buffer.get_iter_at_mark(buffer.get_insert())
        self.state["cursor_position"] = cursor.get_offset()

        # UI state
        self.state["webview_hidden"] = webview_hidden

        self.save_state()

    def restore_all(self, window, sidebar):
        """Restore all state."""
        # Window size
        window_state = self.get_window_state()
        window.set_default_size(
            window_state.get("width", 850), window_state.get("height", 750)
        )

        if window_state.get("maximized", False):
            window.maximize()

        # Content
        content = self.get_content()
        if content:
            sidebar.set_text(content)

            # Restore cursor position
            cursor_pos = self.get_cursor_position()
            buffer = sidebar.buffer
            cursor_iter = buffer.get_iter_at_offset(cursor_pos)
            buffer.place_cursor(cursor_iter)

        return self.is_webview_hidden()
