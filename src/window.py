import gi
import threading
from concurrent.futures import ThreadPoolExecutor
import time

gi.require_version(namespace="Gtk", version="4.0")
gi.require_version(namespace="Adw", version="1")

from gi.repository import Adw, Gtk, Gio, GLib
from src.sidebar import SidebarWidget
from src.webview import WebViewWidget
from src.state_manager import StateManager
from src.file_manager import FileManagerDialog, FileHistory
from src.export_dialog import ExportDialog
from src.shortcuts_window import ShortcutsWindow

import comrak
import os

UI_FILE = "ui/window.ui"


@Gtk.Template(filename=UI_FILE)
class Window(Adw.ApplicationWindow):
    __gtype_name__ = "Window"

    toggle_sidebar_btn = Gtk.Template.Child()
    toggle_sync_scroll_btn = Gtk.Template.Child()
    adw_overlay_split_view = Gtk.Template.Child()
    adw_multi_layout_view = Gtk.Template.Child()

    # Desktop containers
    sidebar_container = Gtk.Template.Child()
    webview_container = Gtk.Template.Child()

    # Mobile containers
    mobile_sidebar_container = Gtk.Template.Child()
    mobile_webview_container = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.is_mobile = False
        self.webview_hidden = False
        self.content_modified = False
        self.current_file = None
        self.sync_scroll_enabled = True

        # Thread pool for parallel operations
        self._thread_pool = ThreadPoolExecutor(max_workers=6)

        # Debounce timer for text updates
        self._update_timer_id = None
        self._pending_text = None
        self._rendering_lock = threading.Lock()

        # Initialize file history
        self.file_history = FileHistory()

        # Initialize state manager
        self.state_manager = StateManager()

        # Add file operation buttons to headerbar
        self._setup_headerbar_buttons()

        # Connect sidebar toggle button
        self.toggle_sidebar_btn.connect("clicked", self._on_toggle_sidebar)

        # Connect scroll sync toggle button
        self.toggle_sync_scroll_btn.connect("clicked", self._on_toggle_sync_scroll)

        # Create widgets
        self.sidebar_widget = SidebarWidget(parent_window=self)
        self.webview_widget = WebViewWidget()

        # Configure comrak extension options
        self.extension_options = comrak.ExtensionOptions()
        self.extension_options.table = True
        self.extension_options.strikethrough = True
        self.extension_options.autolink = True
        self.extension_options.tasklist = True
        self.extension_options.superscript = True
        self.extension_options.footnotes = True

        # Desktop view initially
        self.sidebar_container.append(self.sidebar_widget)
        self.webview_container.append(self.webview_widget)

        # Restore state first
        self._restore_state()

        # If no saved content, show welcome message
        if not self.sidebar_widget.get_text():
            initial_text = """# Welcome to ProPad

## Features

- **Live Preview** with synchronized scrolling
- **Markdown Tables** support
- **Mermaid Diagrams** rendering
- **LaTeX Math** equations
- **GitHub Alerts** (Note, Tip, Important, Warning, Caution)
- **File History** with tags

> [!NOTE]
> This is a GitHub-style note alert!

Start editing to see the preview!"""

            self.sidebar_widget.set_text(initial_text)
            self._render_markdown_async(initial_text)
        else:
            text = self.sidebar_widget.get_text()
            self._render_markdown_async(text)

        # Connect to text buffer changes with debouncing
        def on_text_update(text):
            self._debounced_render(text)
            self.content_modified = True
            self._update_title()

            # Track file edits
            if self.current_file:
                self.file_history.add_file(self.current_file, "edited")

        self.sidebar_widget.connect_text_changed(on_text_update)

        # Connect hide webview button
        self.sidebar_widget.connect_hide_webview(self._on_hide_webview)

        # Setup bidirectional scroll sync
        self._setup_bidirectional_scroll_sync()

        # Show sidebar by default on desktop
        sidebar_visible = self.state_manager.is_sidebar_visible()
        self.adw_overlay_split_view.set_show_sidebar(sidebar_visible)

        # Listen for layout changes
        self.adw_multi_layout_view.connect(
            "notify::layout-name", self._on_layout_changed
        )

        # Set initial layout
        self._on_layout_changed(self.adw_multi_layout_view, None)

        # Update title
        self._update_title()

        # Update sync scroll button state
        self._update_sync_scroll_button()

        # Connect window close event to save state
        self.connect("close-request", self._on_close_request)

        # Auto-save timer (every 30 seconds)
        GLib.timeout_add_seconds(30, self._auto_save_state)

    def _setup_bidirectional_scroll_sync(self):
        """Setup lightweight bidirectional scroll synchronization."""
        # Initialize scroll tracking
        self._last_sidebar_percentage = 0.0
        self._last_webview_percentage = 0.0
        self._scroll_lock = False

        print("🚀 Setting up lightweight bidirectional scroll sync...")

        # DIRECTION 1: Sidebar → WebView (Editor scrolls, Preview follows)
        def on_sidebar_scroll(percentage):
            if self.sync_scroll_enabled and not self._scroll_lock:
                # Larger threshold to reduce updates
                if abs(percentage - self._last_sidebar_percentage) > 0.005:
                    self._last_sidebar_percentage = percentage
                    self._scroll_lock = True

                    # Scroll webview
                    self.webview_widget.scroll_to_percentage(percentage)

                    # Reset lock
                    GLib.timeout_add(100, lambda: setattr(self, "_scroll_lock", False))

        self.sidebar_widget.connect_scroll_changed(on_sidebar_scroll)
        print("✅ Sidebar → WebView sync enabled")

        # DIRECTION 2: WebView → Sidebar (Preview scrolls, Editor follows)
        def on_webview_scroll(percentage):
            if self.sync_scroll_enabled and not self._scroll_lock:
                # Larger threshold to reduce updates
                if abs(percentage - self._last_webview_percentage) > 0.005:
                    self._last_webview_percentage = percentage
                    self._scroll_lock = True

                    # Scroll sidebar
                    self.sidebar_widget.scroll_to_percentage(percentage)

                    # Reset lock
                    GLib.timeout_add(100, lambda: setattr(self, "_scroll_lock", False))

        self.webview_widget.connect_scroll_changed(on_webview_scroll)
        print("✅ WebView → Sidebar sync enabled")

        print("✨ Lightweight bidirectional scroll sync complete!")

    def _on_toggle_sync_scroll(self, button):
        """Toggle scroll synchronization."""
        self.sync_scroll_enabled = not self.sync_scroll_enabled

        # Update both widgets
        self.sidebar_widget.set_sync_scroll_enabled(self.sync_scroll_enabled)
        self.webview_widget.set_sync_scroll_enabled(self.sync_scroll_enabled)

        # Save to state
        self.state_manager.state["sync_scroll_enabled"] = self.sync_scroll_enabled
        self.state_manager.save_state()

        # Update button
        self._update_sync_scroll_button()

    def _update_sync_scroll_button(self):
        """Update sync scroll button appearance."""
        if self.sync_scroll_enabled:
            self.toggle_sync_scroll_btn.set_icon_name("view-dual-symbolic")
            self.toggle_sync_scroll_btn.set_tooltip_text(
                "Sync Scroll Enabled (Ctrl+Alt+S)"
            )
            self.toggle_sync_scroll_btn.remove_css_class("dim-label")
        else:
            self.toggle_sync_scroll_btn.set_icon_name("view-paged-symbolic")
            self.toggle_sync_scroll_btn.set_tooltip_text(
                "Sync Scroll Disabled (Ctrl+Alt+S)"
            )
            self.toggle_sync_scroll_btn.add_css_class("dim-label")

    def _debounced_render(self, text):
        """Debounce text rendering to avoid excessive updates."""
        self._pending_text = text

        if self._update_timer_id:
            GLib.source_remove(self._update_timer_id)

        # Wait 100ms before rendering (faster for better responsiveness)
        self._update_timer_id = GLib.timeout_add(100, self._process_pending_text)

        def _setup_bidirectional_scroll_sync(self):
            """Setup ultra-smooth 120fps bidirectional scroll synchronization."""
            # Initialize scroll tracking
            self._last_sidebar_percentage = 0.0
            self._last_webview_percentage = 0.0
            self._scroll_lock = False

            print("🚀 Setting up ultra-smooth 120fps bidirectional scroll sync...")

            # DIRECTION 1: Sidebar → WebView (Editor scrolls, Preview follows)
            def on_sidebar_scroll(percentage):
                if self.sync_scroll_enabled and not self._scroll_lock:
                    # Fine-grained threshold for smooth tracking
                    if abs(percentage - self._last_sidebar_percentage) > 0.001:
                        self._last_sidebar_percentage = percentage
                        self._scroll_lock = True

                        # Scroll webview with animation
                        self.webview_widget.scroll_to_percentage(percentage)

                        # Quick unlock for continuous scrolling (200ms to allow animation)
                        GLib.timeout_add(
                            200, lambda: setattr(self, "_scroll_lock", False)
                        )

            self.sidebar_widget.connect_scroll_changed(on_sidebar_scroll)
            print("✅ Sidebar → WebView sync enabled (120fps)")

            # DIRECTION 2: WebView → Sidebar (Preview scrolls, Editor follows)
            def on_webview_scroll(percentage):
                if self.sync_scroll_enabled and not self._scroll_lock:
                    # Fine-grained threshold for smooth tracking
                    if abs(percentage - self._last_webview_percentage) > 0.001:
                        self._last_webview_percentage = percentage
                        self._scroll_lock = True

                        # Scroll sidebar with animation
                        self.sidebar_widget.scroll_to_percentage(percentage)

                        # Quick unlock for continuous scrolling (200ms to allow animation)
                        GLib.timeout_add(
                            200, lambda: setattr(self, "_scroll_lock", False)
                        )

            self.webview_widget.connect_scroll_changed(on_webview_scroll)
            print("✅ WebView → Sidebar sync enabled (120fps)")

            print("✨ Ultra-smooth 120fps bidirectional scroll sync complete!")

    def _process_pending_text(self):
        """Process pending text after debounce period."""
        if self._pending_text is not None:
            self._render_markdown_async(self._pending_text)
            self._pending_text = None
        self._update_timer_id = None
        return False

    def _render_markdown_async(self, text):
        """Render markdown in background thread."""

        def _setup_bidirectional_scroll_sync(self):
            """Setup optimized bidirectional scroll synchronization."""
            # Initialize scroll tracking
            self._last_sidebar_percentage = 0.0
            self._last_webview_percentage = 0.0
            self._scroll_lock = False

            print("🚀 Setting up optimized bidirectional scroll sync...")

            # DIRECTION 1: Sidebar → WebView (Editor scrolls, Preview follows)
            def on_sidebar_scroll(percentage):
                if self.sync_scroll_enabled and not self._scroll_lock:
                    # Balanced threshold
                    if abs(percentage - self._last_sidebar_percentage) > 0.003:
                        self._last_sidebar_percentage = percentage
                        self._scroll_lock = True

                        # Scroll webview with animation
                        self.webview_widget.scroll_to_percentage(percentage)

                        # Reset lock after animation
                        GLib.timeout_add(
                            150, lambda: setattr(self, "_scroll_lock", False)
                        )

            self.sidebar_widget.connect_scroll_changed(on_sidebar_scroll)
            print("✅ Sidebar → WebView sync enabled")

            # DIRECTION 2: WebView → Sidebar (Preview scrolls, Editor follows)
            def on_webview_scroll(percentage):
                if self.sync_scroll_enabled and not self._scroll_lock:
                    # Balanced threshold
                    if abs(percentage - self._last_webview_percentage) > 0.003:
                        self._last_webview_percentage = percentage
                        self._scroll_lock = True

                        # Scroll sidebar instantly for better text rendering
                        self.sidebar_widget.scroll_to_percentage(percentage)

                        # Reset lock quickly
                        GLib.timeout_add(
                            100, lambda: setattr(self, "_scroll_lock", False)
                        )

            self.webview_widget.connect_scroll_changed(on_webview_scroll)
            print("✅ WebView → Sidebar sync enabled")

            print("✨ Optimized bidirectional scroll sync complete!")

        def render():
            with self._rendering_lock:
                try:
                    # Render markdown with GPU acceleration
                    html = comrak.render_markdown(
                        text, extension_options=self.extension_options
                    )

                    # Load HTML in main thread (WebKit requires main thread)
                    GLib.idle_add(
                        lambda: self.webview_widget.load_html(
                            html, is_dark=self.is_dark_mode()
                        )
                    )
                except Exception as e:
                    print(f"Error rendering markdown: {e}")

        # Submit to thread pool
        self._thread_pool.submit(render)

    def _setup_headerbar_buttons(self):
        """Add file operation buttons to the headerbar."""
        # New file action (Ctrl+N)
        new_action = Gio.SimpleAction.new("new-file", None)
        new_action.connect("activate", self._on_new_file)
        self.add_action(new_action)

        # Open file action (Ctrl+O)
        open_action = Gio.SimpleAction.new("open-file", None)
        open_action.connect("activate", self._on_open_file)
        self.add_action(open_action)

        # Save file action (Ctrl+S)
        save_action = Gio.SimpleAction.new("save-file", None)
        save_action.connect("activate", self._on_save_file)
        self.add_action(save_action)

        # Save as action (Ctrl+Shift+S)
        save_as_action = Gio.SimpleAction.new("save-as", None)
        save_as_action.connect("activate", self._on_save_as)
        self.add_action(save_as_action)

        # Toggle sync scroll action (Ctrl+Alt+S)
        toggle_sync_action = Gio.SimpleAction.new("toggle-sync-scroll", None)
        toggle_sync_action.connect(
            "activate", lambda a, p: self._on_toggle_sync_scroll(None)
        )
        self.add_action(toggle_sync_action)

    def _on_new_file(self, action, param):
        """Create new file and track in history."""
        if self.content_modified:
            dialog = Adw.MessageDialog.new(self)
            dialog.set_heading("Save Changes?")
            dialog.set_body(
                "The document has unsaved changes. Do you want to save them?"
            )
            dialog.add_response("discard", "Discard")
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("save", "Save")
            dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_response_appearance(
                "discard", Adw.ResponseAppearance.DESTRUCTIVE
            )
            dialog.connect("response", self._on_new_file_response)
            dialog.present()
        else:
            self._create_new_file()

    def _on_new_file_response(self, dialog, response):
        """Handle new file save response."""
        if response == "save":
            if self.current_file:
                self._save_to_file(self.current_file)
                GLib.timeout_add(100, self._create_new_file)
            else:
                self._save_as_for_new = True
                self._on_save_as(None, None)
        elif response == "discard":
            self._create_new_file()

    def _create_new_file(self):
        """Create new empty file."""
        self.sidebar_widget.set_text("")
        self.current_file = None
        self.content_modified = False
        self._update_title()
        return False

    def _on_open_file(self, action, param):
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

        dialog.open(self, None, self._on_open_file_response)

    def _on_open_file_response(self, dialog, result):
        """Handle file open response - load in background."""
        try:
            file = dialog.open_finish(result)
            if file:
                filepath = file.get_path()

                # Load file in background thread
                def load_file_async():
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Update UI in main thread
                        GLib.idle_add(lambda: self._finish_file_load(filepath, content))
                    except Exception as e:
                        print(f"Error loading file: {e}")
                        GLib.idle_add(
                            lambda: self._show_error_toast(f"Error loading file: {e}")
                        )

                self._thread_pool.submit(load_file_async)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"Error opening file: {e}")

    def _finish_file_load(self, filepath, content):
        """Finish loading file in main thread."""
        self.sidebar_widget.set_text(content)
        self.current_file = filepath
        self.content_modified = False
        self._update_title()
        self.state_manager.save_current_file(filepath)

        # Track in file history
        self.file_history.add_file(filepath, "opened")

    def _on_save_file(self, action, param):
        """Save current file."""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._on_save_as(action, param)

    def _on_save_as(self, action, param):
        """Save as dialog."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Markdown File")

        if self.current_file:
            initial_name = os.path.basename(self.current_file)
        else:
            initial_name = "untitled.md"

        dialog.set_initial_name(initial_name)
        dialog.save(self, None, self._on_save_as_response)

    def _on_save_as_response(self, dialog, result):
        """Handle save as response."""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()
                if not filepath.endswith((".md", ".markdown", ".txt")):
                    filepath += ".md"

                is_new = not os.path.exists(filepath)
                self._save_to_file(filepath, is_new=is_new)
                self.current_file = filepath
                self._update_title()

                if hasattr(self, "_save_as_for_new") and self._save_as_for_new:
                    self._save_as_for_new = False
                    GLib.timeout_add(200, self._create_new_file)

        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"Error saving file: {e}")

    def _save_to_file(self, filepath, is_new=False):
        """Save content to file in background."""
        content = self.sidebar_widget.get_text()

        def save_async():
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

                GLib.idle_add(lambda: self._finish_file_save(filepath, is_new))
            except Exception as e:
                print(f"Error saving file: {e}")
                GLib.idle_add(lambda: self._show_error_toast(f"Error saving: {e}"))

        self._thread_pool.submit(save_async)

    def _finish_file_save(self, filepath, is_new=False):
        """Finish saving file in main thread."""
        self.content_modified = False
        self._update_title()
        print(f"File saved: {filepath}")

        # Track in file history
        action = "created" if is_new else "edited"
        self.file_history.add_file(filepath, action)

    def _show_error_toast(self, message):
        """Show error message."""
        print(f"Error: {message}")

    def _on_file_manager_activate(self, action, param):
        """Show file manager dialog."""
        dialog = FileManagerDialog(self)
        dialog.current_file = self.current_file
        dialog.entry_current_file.set_text(self.current_file or "Untitled.md")
        dialog.present()

    def _on_export_activate(self, action, param):
        """Show export dialog."""
        dialog = ExportDialog(self)
        dialog.present()

    def _on_shortcuts_activate(self, action, param):
        """Show keyboard shortcuts window."""
        shortcuts_window = ShortcutsWindow(parent=self)
        shortcuts_window.present()

    def _on_about_activate(self, action, param):
        """Show about dialog."""
        about = Adw.AboutDialog.new()
        about.set_application_name("ProPad")
        about.set_application_icon("text-editor-symbolic")
        about.set_developer_name("ProPad Team")
        about.set_version("2.0.0")
        about.set_website("https://github.com/yourusername/propad")
        about.set_issue_url("https://github.com/yourusername/propad/issues")
        about.set_copyright("© 2024 ProPad Team")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_developers(["ProPad Contributors", "Built with PyGObject and GTK4"])
        about.set_comments(
            "A modern Markdown editor with live preview, "
            "GPU-accelerated rendering, synchronized scrolling, "
            "file history tracking, and support for tables, "
            "Mermaid diagrams, LaTeX math, and GitHub alerts."
        )
        about.present(self)

    def _restore_state(self):
        """Restore application state."""
        window_state = self.state_manager.get_window_state()
        self.set_default_size(
            window_state.get("width", 950), window_state.get("height", 750)
        )

        if window_state.get("maximized", False):
            self.maximize()

        content = self.state_manager.get_content()
        if content:
            self.sidebar_widget.set_text(content)
            cursor_pos = self.state_manager.get_cursor_position()
            self.sidebar_widget.set_cursor_position(cursor_pos)

        self.current_file = self.state_manager.get_current_file()
        self.webview_hidden = self.state_manager.is_webview_hidden()
        self.sync_scroll_enabled = self.state_manager.state.get(
            "sync_scroll_enabled", True
        )

        # Update widgets with sync scroll state
        self.sidebar_widget.set_sync_scroll_enabled(self.sync_scroll_enabled)
        self.webview_widget.set_sync_scroll_enabled(self.sync_scroll_enabled)

        if self.webview_hidden:
            GLib.idle_add(self._apply_webview_hidden_state)

        self.content_modified = False

    def _apply_webview_hidden_state(self):
        """Apply the webview hidden state to UI."""
        if self.webview_hidden:
            if not self.is_mobile:
                self.adw_overlay_split_view.set_collapsed(True)
                self.adw_overlay_split_view.set_show_sidebar(True)
            else:
                self.mobile_webview_container.set_visible(False)

            self.sidebar_widget.hide_webview_btn.set_icon_name("view-reveal-symbolic")
            self.sidebar_widget.hide_webview_btn.set_tooltip_text("Show Preview")
        else:
            if not self.is_mobile:
                self.adw_overlay_split_view.set_collapsed(False)
                self.adw_overlay_split_view.set_show_sidebar(True)
            else:
                self.mobile_webview_container.set_visible(True)

            self.sidebar_widget.hide_webview_btn.set_icon_name("window-close-symbolic")
            self.sidebar_widget.hide_webview_btn.set_tooltip_text("Hide Preview")

    def _auto_save_state(self):
        """Auto-save state periodically."""
        self._save_state()
        return True

    def _save_state(self):
        """Save current application state in background."""

        def save_async():
            width, height = self.get_default_size()
            self.state_manager.state["window"] = {
                "width": width,
                "height": height,
                "maximized": self.is_maximized(),
            }

            self.state_manager.save_content(self.sidebar_widget.get_text())
            cursor_pos = self.sidebar_widget.get_cursor_position()
            self.state_manager.save_cursor_position(cursor_pos)
            self.state_manager.save_current_file(self.current_file)

            sidebar_visible = self.adw_overlay_split_view.get_show_sidebar()
            self.state_manager.save_sidebar_visible(sidebar_visible)
            self.state_manager.save_webview_hidden(self.webview_hidden)

            # Save sync scroll state
            self.state_manager.state["sync_scroll_enabled"] = self.sync_scroll_enabled
            self.state_manager.save_state()

        self._thread_pool.submit(save_async)

    def _on_close_request(self, window):
        """Handle window close request."""
        self._save_state()
        time.sleep(0.1)
        return False

    def _update_title(self):
        """Update window title based on current file and modification state."""
        if self.current_file:
            filename = os.path.basename(self.current_file)
            if self.content_modified:
                self.set_title(f"● {filename} - ProPad")
            else:
                self.set_title(f"{filename} - ProPad")
        else:
            if self.content_modified:
                self.set_title("● Untitled - ProPad")
            else:
                self.set_title("ProPad")

    def set_current_file(self, filepath):
        """Set current file and update state."""
        self.current_file = filepath
        self.content_modified = False
        self._update_title()
        self.state_manager.save_current_file(filepath)

    def mark_content_modified(self, modified: bool = True):
        """Mark content as modified."""
        self.content_modified = modified
        self._update_title()

    def is_dark_mode(self) -> bool:
        """Check if the current GTK theme is dark."""
        style_manager = Adw.StyleManager.get_default()
        return style_manager.get_dark()

    def _on_toggle_sidebar(self, button: Gtk.Button) -> None:
        """Toggle sidebar visibility."""
        current = self.adw_overlay_split_view.get_show_sidebar()
        self.adw_overlay_split_view.set_show_sidebar(not current)
        self.state_manager.save_sidebar_visible(not current)

    def _on_hide_webview(self) -> None:
        """Toggle webview visibility."""
        self.webview_hidden = not self.webview_hidden

        if self.webview_hidden:
            if not self.is_mobile:
                self.adw_overlay_split_view.set_collapsed(True)
                self.adw_overlay_split_view.set_show_sidebar(True)
            else:
                self.mobile_webview_container.set_visible(False)

            self.sidebar_widget.hide_webview_btn.set_icon_name("view-reveal-symbolic")
            self.sidebar_widget.hide_webview_btn.set_tooltip_text("Show Preview")
        else:
            if not self.is_mobile:
                self.adw_overlay_split_view.set_collapsed(False)
                self.adw_overlay_split_view.set_show_sidebar(True)
            else:
                self.mobile_webview_container.set_visible(True)

            self.sidebar_widget.hide_webview_btn.set_icon_name("window-close-symbolic")
            self.sidebar_widget.hide_webview_btn.set_tooltip_text("Hide Preview")

        self.state_manager.save_webview_hidden(self.webview_hidden)

    def _on_layout_changed(self, multi_layout: Adw.MultiLayoutView, _) -> None:
        """Handle layout changes between desktop and mobile."""
        layout_name = multi_layout.get_layout_name()

        if layout_name == "mobile" and not self.is_mobile:
            self._switch_to_mobile()
        elif layout_name == "desktop" and self.is_mobile:
            self._switch_to_desktop()

    def _switch_to_mobile(self) -> None:
        """Switch to mobile layout."""
        self.is_mobile = True

        parent = self.sidebar_widget.get_parent()
        if parent:
            parent.remove(self.sidebar_widget)

        parent = self.webview_widget.get_parent()
        if parent:
            parent.remove(self.webview_widget)

        self.mobile_sidebar_container.append(self.sidebar_widget)
        self.mobile_webview_container.append(self.webview_widget)
        self.mobile_webview_container.set_visible(not self.webview_hidden)

    def _switch_to_desktop(self) -> None:
        """Switch to desktop layout."""
        self.is_mobile = False

        parent = self.sidebar_widget.get_parent()
        if parent:
            parent.remove(self.sidebar_widget)

        parent = self.webview_widget.get_parent()
        if parent:
            parent.remove(self.webview_widget)

        self.sidebar_container.append(self.sidebar_widget)
        self.webview_container.append(self.webview_widget)

        if self.webview_hidden:
            self.adw_overlay_split_view.set_collapsed(True)
            self.adw_overlay_split_view.set_show_sidebar(True)
        else:
            self.adw_overlay_split_view.set_collapsed(False)
            self.adw_overlay_split_view.set_show_sidebar(True)

    def get_sidebar(self) -> SidebarWidget:
        """Get the sidebar widget."""
        return self.sidebar_widget

    def get_webview(self) -> WebViewWidget:
        """Get the webview widget."""
        return self.webview_widget
