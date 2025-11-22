import gi
from concurrent.futures import ThreadPoolExecutor

gi.require_version(namespace="Gtk", version="4.0")

from gi.repository import Gtk, Gdk, GLib
from search_replace import SearchReplaceBar
from formatting_toolbar import FormattingToolbar

UI_FILE = "ui/sidebar.ui"


@Gtk.Template(filename=UI_FILE)
class SidebarWidget(Gtk.Box):
    __gtype_name__ = "SidebarWidget"

    textview = Gtk.Template.Child()
    hide_webview_btn = Gtk.Template.Child()
    btn_formatting = Gtk.Template.Child()
    search_container = Gtk.Template.Child()

    def __init__(self, parent_window=None, **kwargs):
        if "orientation" not in kwargs:
            kwargs["orientation"] = Gtk.Orientation.VERTICAL
        super().__init__(**kwargs)

        self.parent_window = parent_window
        self.buffer = self.textview.get_buffer()

        # Thread pool for async operations
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

        # Custom callbacks
        self._text_changed_callbacks = []
        self._hide_webview_callbacks = []
        self._scroll_callbacks = []

        # Ultra-smooth scroll state (120fps support)
        self.sync_scroll_enabled = True
        self._is_programmatic_scroll = False
        self._scroll_adjustment = None
        self._last_scroll_value = 0.0
        self._target_scroll_value = 0.0
        self._scroll_velocity = 0.0
        self._scroll_poll_id = None
        self._scroll_animation_id = None  # Initialize as None

        # Connect signals
        self.buffer.connect("changed", self._on_buffer_changed)
        self.hide_webview_btn.connect("clicked", self._on_hide_webview_clicked)

        # Setup search/replace bar
        self.search_bar = SearchReplaceBar(self.textview)
        self.search_bar.set_visible(False)
        self.search_container.append(self.search_bar)

        # Setup formatting toolbar
        self.formatting_toolbar = FormattingToolbar(self.textview, parent_window)
        self.btn_formatting.set_popover(self.formatting_toolbar)

        # Setup keyboard shortcuts
        self._setup_shortcuts()

        # Setup scroll sync - delayed to ensure parent is ready
        GLib.idle_add(self._setup_scroll_sync)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.textview.add_controller(key_controller)

    def _setup_scroll_sync(self):
        """Setup optimized scroll polling."""
        parent = self.textview.get_parent()

        # Find ScrolledWindow parent
        max_depth = 8
        depth = 0
        while parent and depth < max_depth:
            if isinstance(parent, Gtk.ScrolledWindow):
                vadjustment = parent.get_vadjustment()
                if vadjustment:
                    self._scroll_adjustment = vadjustment
                    # Use 60fps for better stability
                    if self._scroll_poll_id:
                        GLib.source_remove(self._scroll_poll_id)
                    self._scroll_poll_id = GLib.timeout_add(16, self._poll_scroll)
                    print("✅ Sidebar scroll sync polling (60fps) setup successful!")
                    return False
            parent = parent.get_parent()
            depth += 1

        print("⚠ Warning: Could not find ScrolledWindow parent for scroll sync")
        return False

    def _poll_scroll(self):
        """Poll scroll at 60fps for stable tracking."""
        if (
            not self.sync_scroll_enabled
            or self._is_programmatic_scroll
            or not self._scroll_adjustment
        ):
            return True

        try:
            value = self._scroll_adjustment.get_value()
            upper = self._scroll_adjustment.get_upper()
            page_size = self._scroll_adjustment.get_page_size()

            max_scroll = upper - page_size
            if max_scroll <= 0:
                percentage = 0.0
            else:
                percentage = value / max_scroll

            # Balanced threshold for smooth tracking without overhead
            if abs(percentage - self._last_scroll_value) > 0.003:
                self._last_scroll_value = percentage

                # Notify callbacks directly
                for callback in self._scroll_callbacks:
                    try:
                        callback(percentage)
                    except Exception as e:
                        print(f"Error in scroll callback: {e}")
        except Exception as e:
            print(f"Sidebar poll error: {e}")

        return True

    def scroll_to_percentage(self, percentage: float):
        """Scroll smoothly with optimized rendering."""
        if not self.sync_scroll_enabled or not self._scroll_adjustment:
            return

        self._is_programmatic_scroll = True
        self._target_scroll_value = max(0.0, min(1.0, percentage))

        upper = self._scroll_adjustment.get_upper()
        page_size = self._scroll_adjustment.get_page_size()
        max_scroll = upper - page_size

        if max_scroll <= 0:
            self._is_programmatic_scroll = False
            return

        target_value = max_scroll * percentage
        current_value = self._scroll_adjustment.get_value()

        # Use instant scroll to avoid rendering lag
        self._scroll_adjustment.set_value(target_value)
        self._last_scroll_value = percentage

        # Quick reset to allow user scrolling
        GLib.timeout_add(
            100, lambda: setattr(self, "_is_programmatic_scroll", False) or False
        )

    def connect_scroll_changed(self, callback):
        """Register a callback for scroll changes."""
        self._scroll_callbacks.append(callback)
        print(f"✅ Scroll callback registered. Total: {len(self._scroll_callbacks)}")

    def set_sync_scroll_enabled(self, enabled: bool):
        """Enable or disable synchronized scrolling."""
        self.sync_scroll_enabled = enabled
        print(f"✅ Sync scroll {'enabled' if enabled else 'disabled'}")

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts."""
        ctrl_pressed = state & Gdk.ModifierType.CONTROL_MASK

        if ctrl_pressed:
            # Ctrl+F: Find
            if keyval == Gdk.KEY_f:
                self.search_bar.show_search()
                return True

            # Ctrl+H: Find and Replace
            elif keyval == Gdk.KEY_h:
                self.search_bar.show_replace()
                return True

            # Ctrl+B: Bold
            elif keyval == Gdk.KEY_b:
                self._wrap_selection("**", "**")
                return True

            # Ctrl+I: Italic
            elif keyval == Gdk.KEY_i:
                self._wrap_selection("*", "*")
                return True

            # Ctrl+K: Insert link
            elif keyval == Gdk.KEY_k:
                self.formatting_toolbar.btn_link.emit("clicked")
                return True

        return False

    def _wrap_selection(self, prefix, suffix):
        """Wrap selected text with prefix and suffix."""
        bounds = self.buffer.get_selection_bounds()
        if bounds:
            start, end = bounds
            text = self.buffer.get_text(start, end, True)
            self.buffer.delete(start, end)
            self.buffer.insert(start, f"{prefix}{text}{suffix}")
        else:
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert(cursor, f"{prefix}text{suffix}")

    def _on_buffer_changed(self, buffer):
        """Call all registered callbacks when text changes."""
        for callback in self._text_changed_callbacks:
            callback(self.get_text())

    def _on_hide_webview_clicked(self, button):
        """Call all registered callbacks when hide button is clicked."""
        for callback in self._hide_webview_callbacks:
            callback()

    def connect_text_changed(self, callback):
        """Register a callback for text changes."""
        self._text_changed_callbacks.append(callback)

    def connect_hide_webview(self, callback):
        """Register a callback for hide webview button."""
        self._hide_webview_callbacks.append(callback)

    def get_text(self):
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        return self.buffer.get_text(start_iter, end_iter, True)

    def set_text(self, text: str):
        """Set text and trigger callbacks."""
        self.buffer.set_text(text)
        for callback in self._text_changed_callbacks:
            callback(text)

    def clear(self):
        self.buffer.set_text("")
        for callback in self._text_changed_callbacks:
            callback("")

    def get_cursor_position(self):
        """Get cursor position offset."""
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        return cursor.get_offset()

    def set_cursor_position(self, offset):
        """Set cursor position."""
        cursor_iter = self.buffer.get_iter_at_offset(offset)
        self.buffer.place_cursor(cursor_iter)
