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

        # Custom callbacks list
        self._text_changed_callbacks = []
        self._hide_webview_callbacks = []
        self._scroll_callbacks = []

        # Sync scroll state with smooth animation
        self.sync_scroll_enabled = True
        self._is_programmatic_scroll = False
        self._scroll_adjustment = None
        self._last_scroll_value = 0.0
        self._target_scroll_value = 0.0
        self._scroll_animation_id = None
        self._scroll_poll_id = None

        # Connect GTK buffer "changed" signal
        self.buffer.connect("changed", self._on_buffer_changed)

        # Connect hide button
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

        # Setup scroll synchronization - delayed to ensure parent is ready
        GLib.idle_add(self._setup_scroll_sync)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.textview.add_controller(key_controller)

    def _setup_scroll_sync(self):
        """Setup 60fps scroll polling to keep sidebar in sync with webview."""
        # Find the scrolled window parent
        parent = self.textview.get_parent()

        # Walk up the widget tree to find ScrolledWindow
        max_depth = 8
        depth = 0
        while parent and depth < max_depth:
            if isinstance(parent, Gtk.ScrolledWindow):
                vadjustment = parent.get_vadjustment()
                if vadjustment:
                    self._scroll_adjustment = vadjustment
                    # Use 60fps polling so we can reliably calculate percentage and animate smoothly.
                    # Poll interval: ~16ms = ~60fps
                    if self._scroll_poll_id:
                        GLib.source_remove(self._scroll_poll_id)
                    self._scroll_poll_id = GLib.timeout_add(16, self._poll_scroll)
                    print("✓ Sidebar scroll sync polling (60fps) setup successful!")
                    return False
            parent = parent.get_parent()
            depth += 1

        print("⚠ Warning: Could not find ScrolledWindow parent for scroll sync")
        return False

    def _poll_scroll(self):
        """Poll the adjustment at ~60fps and notify callbacks when percentage changes."""
        if (
            not self.sync_scroll_enabled
            or self._is_programmatic_scroll
            or not self._scroll_adjustment
        ):
            return True  # continue polling

        try:
            value = self._scroll_adjustment.get_value()
            upper = self._scroll_adjustment.get_upper()
            page_size = self._scroll_adjustment.get_page_size()

            max_scroll = upper - page_size
            if max_scroll <= 0:
                percentage = 0.0
            else:
                percentage = value / max_scroll

            # smaller threshold for high responsiveness
            if abs(percentage - self._last_scroll_value) > 0.001:
                self._last_scroll_value = percentage

                # Notify scroll callbacks (webview) in main loop via threadpool for non-blocking
                def notify_callbacks():
                    for callback in self._scroll_callbacks:
                        try:
                            GLib.idle_add(
                                lambda p=percentage, c=callback: (c(p), False)[1]
                            )
                        except Exception as e:
                            print(f"Error in scroll callback: {e}")

                self._thread_pool.submit(notify_callbacks)
        except Exception as e:
            # keep polling even if something goes wrong
            print(f"Sidebar poll error: {e}")

        return True  # keep polling at ~60fps

    def _on_scroll_changed(self, adjustment):
        """Legacy handler (kept for compatibility)."""
        # We prefer polling at 60fps. Keep handler minimal in case it's used.
        if not self.sync_scroll_enabled or self._is_programmatic_scroll:
            return
        # Trigger immediate poll to keep values fresh
        self._poll_scroll()

    def scroll_to_percentage(self, percentage: float):
        """Scroll textview to a specific percentage with GPU-accelerated smooth animation."""
        if not self.sync_scroll_enabled or not self._scroll_adjustment:
            return

        self._is_programmatic_scroll = True
        self._target_scroll_value = percentage

        upper = self._scroll_adjustment.get_upper()
        page_size = self._scroll_adjustment.get_page_size()
        max_scroll = upper - page_size

        if max_scroll <= 0:
            self._is_programmatic_scroll = False
            return

        target_value = max_scroll * percentage
        current_value = self._scroll_adjustment.get_value()

        # Use easing for ultra-smooth scrolling
        diff = target_value - current_value

        # If difference is small, jump directly
        if abs(diff) < 5:
            self._scroll_adjustment.set_value(target_value)
            self._last_scroll_value = percentage
            # Reset flag after one 60fps tick (16ms)
            GLib.timeout_add(
                16, lambda: setattr(self, "_is_programmatic_scroll", False) or False
            )
        else:
            # Smooth animation for larger jumps
            self._animate_scroll_to(current_value, target_value, percentage)

    def _animate_scroll_to(self, start_value, end_value, target_percentage):
        """Animate scroll with GPU-accelerated easing for butter-smooth experience."""
        start_time = GLib.get_monotonic_time()
        duration = 150  # 150ms for smooth but responsive animation

        def animate():
            if not self._scroll_adjustment:
                self._is_programmatic_scroll = False
                return False

            current_time = GLib.get_monotonic_time()
            elapsed = current_time - start_time

            if elapsed >= duration:
                # Animation complete
                self._scroll_adjustment.set_value(end_value)
                self._last_scroll_value = target_percentage
                self._is_programmatic_scroll = False
                return False

            # Ease-out cubic easing for smooth deceleration
            progress = elapsed / duration
            eased_progress = 1 - pow(1 - progress, 3)

            # Calculate interpolated value
            current_value = start_value + (end_value - start_value) * eased_progress
            self._scroll_adjustment.set_value(current_value)

            return True

        # Run at ~60fps (16ms intervals) for smooth animation
        GLib.timeout_add(7, animate)

    def connect_scroll_changed(self, callback):
        """Register a callback for scroll changes."""
        self._scroll_callbacks.append(callback)
        print(f"✓ Scroll callback registered. Total: {len(self._scroll_callbacks)}")

    def set_sync_scroll_enabled(self, enabled: bool):
        """Enable or disable synchronized scrolling."""
        self.sync_scroll_enabled = enabled
        print(f"✓ Sync scroll {'enabled' if enabled else 'disabled'}")

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
