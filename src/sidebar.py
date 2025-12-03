import gi
from concurrent.futures import ThreadPoolExecutor

gi.require_version(namespace="Gtk", version="4.0")

from gi.repository import Gtk, Gdk, GLib
from src.search_replace import SearchReplaceBar
from src.formatting_toolbar import FormattingToolbar
from src.i18n import _

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
        
        self._prevent_scroll_reset = False
            
            # Connect signals
        self.buffer.connect("changed", self._on_buffer_changed)
            
            # Prevent cursor movements from resetting scroll
        self.textview.set_accepts_tab(True)
        
        
            
            # Store scroll position before cursor operations
        # self.textview.connect("button-press-event", self._on_button_press)

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

        # Create stats label at the bottom
        self._create_stats_label()
        
    # def _on_button_press(self, widget, event):
    #     """Store scroll position before click to prevent reset."""
    #     if self._scroll_adjustment:
    #         self._prevent_scroll_reset = True
    #         self._stored_scroll_value = self._scroll_adjustment.get_value()
    #         # Re-enable after a short delay
    #         GLib.timeout_add(50, lambda: setattr(self, "_prevent_scroll_reset", False))
    #     return False

    def _create_stats_label(self):
        """Create and add statistics label at the bottom."""
        self.stats_label = Gtk.Label()
        self.stats_label.set_halign(Gtk.Align.START)
        self.stats_label.set_margin_start(10)
        self.stats_label.set_margin_end(10)
        self.stats_label.set_margin_top(5)
        self.stats_label.set_margin_bottom(5)
        self.stats_label.add_css_class("dim-label")
        self.stats_label.add_css_class("caption")
        self._update_stats()
        self.append(self.stats_label)

    def _update_stats(self):
        """Update word, letter, and paragraph count."""
        text = self.get_text()

        # Count paragraphs (non-empty lines)
        paragraphs = len([line for line in text.split("\n") if line.strip()])

        # Count words (split by whitespace)
        words = len(text.split())

        # Count letters (excluding spaces and newlines)
        letters = len([c for c in text if not c.isspace()])

        # Update label
        # In sidebar.py, line 91-93:
        self.stats_label.set_text(
            f"{_('Words')}: {words}  •  {_('Letters')}: {letters}  •  {_('Paragraphs')}: {paragraphs}"
        )

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

    def get_scroll_percentage(self, callback):
        """Get current scroll percentage."""
        if not self._scroll_adjustment:
            callback(0.0)
            return

        try:
            value = self._scroll_adjustment.get_value()
            upper = self._scroll_adjustment.get_upper()
            page_size = self._scroll_adjustment.get_page_size()

            max_scroll = upper - page_size
            if max_scroll <= 0:
                percentage = 0.0
            else:
                percentage = value / max_scroll

            callback(percentage)
        except Exception as e:
            print(f"Error getting scroll percentage: {e}")
            callback(0.0)

    def scroll_to_percentage(self, percentage: float):
        """Enhanced scroll with better restoration support."""
        if not self._scroll_adjustment:
            print("⚠️ Scroll adjustment not ready yet")
            return

        # Temporarily disable sync to prevent feedback loops during restoration
        was_syncing = self.sync_scroll_enabled
        self.sync_scroll_enabled = False
        self._is_programmatic_scroll = True

        self._target_scroll_value = max(0.0, min(1.0, percentage))

        upper = self._scroll_adjustment.get_upper()
        page_size = self._scroll_adjustment.get_page_size()
        max_scroll = upper - page_size

        if max_scroll <= 0:
            self._is_programmatic_scroll = False
            self.sync_scroll_enabled = was_syncing
            return

        target_value = max_scroll * percentage

        print(
            f"📜 Sidebar scrolling to {percentage:.3f} (value: {target_value:.1f}/{max_scroll:.1f})"
        )

        # Use instant scroll for restoration
        self._scroll_adjustment.set_value(target_value)
        self._last_scroll_value = percentage

        # Re-enable sync after scroll completes
        def reset_flags():
            self._is_programmatic_scroll = False
            self.sync_scroll_enabled = was_syncing
            return False

        GLib.timeout_add(150, reset_flags)

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
        # Store current scroll position
        if self._scroll_adjustment and not self._prevent_scroll_reset:
            current_value = self._scroll_adjustment.get_value()
            
        # Update statistics
        self._update_stats()
    
        # Call text changed callbacks
        for callback in self._text_changed_callbacks:
            callback(self.get_text())
        
        # Restore scroll position if it changed unexpectedly
        if self._scroll_adjustment and not self._prevent_scroll_reset:
            # Use idle_add to restore after GTK's internal scroll adjustments
            def restore_scroll():
                if hasattr(self, '_stored_scroll_value'):
                    self._scroll_adjustment.set_value(current_value)
                return False
            GLib.idle_add(restore_scroll)


    def _on_hide_webview_clicked(self) -> None:
        """Toggle webview visibility."""
        self.webview_hidden = not self.webview_hidden

        if self.webview_hidden:
            if not self.is_mobile:
                self.adw_overlay_split_view.set_collapsed(True)
                self.adw_overlay_split_view.set_show_sidebar(True)
            else:
                self.mobile_webview_container.set_visible(False)

            self.sidebar_widget.hide_webview_btn.set_icon_name("view-reveal-symbolic")
            self.sidebar_widget.hide_webview_btn.set_tooltip_text(_("Show Preview"))
        else:
            if not self.is_mobile:
                self.adw_overlay_split_view.set_collapsed(False)
                self.adw_overlay_split_view.set_show_sidebar(True)
            else:
                self.mobile_webview_container.set_visible(True)

            self.sidebar_widget.hide_webview_btn.set_icon_name("window-close-symbolic")
            self.sidebar_widget.hide_webview_btn.set_tooltip_text(_("Hide Preview"))

        self.state_manager.save_webview_hidden(self.webview_hidden)

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
        """Set text without triggering scroll reset."""
        self._prevent_scroll_reset = True
        
        # Store current scroll before changing text
        if self._scroll_adjustment:
            stored_scroll = self._scroll_adjustment.get_value()
        
        self.buffer.set_text(text)
        self._update_stats()
        
        # # Restore scroll position
        # if self._scroll_adjustment:
        #     GLib.idle_add(lambda: self._scroll_adjustment.set_value(stored_scroll) or False)
        
        for callback in self._text_changed_callbacks:
            callback(text)
        
        # Re-enable after delay
        GLib.timeout_add(100, lambda: setattr(self, "_prevent_scroll_reset", False))

    def clear(self):
        self.buffer.set_text("")
        self._update_stats()
        for callback in self._text_changed_callbacks:
            callback("")

    # def get_cursor_position(self):
    #     """Get cursor position offset."""
    #     cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
    #     return cursor.get_offset()

    # def set_cursor_position(self, offset):
    #     """Set cursor position without resetting scroll."""
    #     self._prevent_scroll_reset = True
        
    #     # Store scroll position
    #     if self._scroll_adjustment:
    #         stored_scroll = self._scroll_adjustment.get_value()
        
    #     cursor_iter = self.buffer.get_iter_at_offset(offset)
    #     self.buffer.place_cursor(cursor_iter)
        
    #     # Restore scroll after cursor placement
    #     if self._scroll_adjustment:
    #         GLib.idle_add(lambda: self._scroll_adjustment.set_value(stored_scroll) or False)
        
    #     GLib.timeout_add(100, lambda: setattr(self, "_prevent_scroll_reset", False))