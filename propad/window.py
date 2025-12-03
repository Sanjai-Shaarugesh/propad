import gi
import threading
from concurrent.futures import ThreadPoolExecutor
import time

gi.require_version(namespace="Gtk", version="4.0")
gi.require_version(namespace="Adw", version="1")

from gi.repository import Adw, Gtk, Gio, GLib
from propad.sidebar import SidebarWidget
from propad.webview import WebViewWidget
from propad.state_manager import StateManager
from propad.file_manager import FileManagerDialog, FileHistory
from propad.export_dialog import ExportDialog
from propad.shortcuts_window import ShortcutsWindow
from propad.i18n import _

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

        self.is_typing = False
        self._typing_debounce_id = None

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self._on_theme_changed)

        # Thread pool for parallel operations
        self._thread_pool = ThreadPoolExecutor(max_workers=6)

        # Debounce timer for text updates
        self._update_timer_id = None
        self._pending_text = None
        self._rendering_lock = threading.Lock()

        self.file_history = FileHistory()

        # Initialize state manager
        self.state_manager = StateManager()

        self._setup_headerbar_buttons()

        self.toggle_sidebar_btn.connect("clicked", self._on_toggle_sidebar)

        self.toggle_sync_scroll_btn.connect("clicked", self._on_toggle_sync_scroll)

        self.sidebar_widget = SidebarWidget(parent_window=self)
        self.webview_widget = WebViewWidget()

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
            initial_text = f"""# {_("Welcome to ProPad")}
        
        ## {_("Features")}
        
        - **{_("Live Preview")}** {_("with synchronized scrolling")}
        - **{_("Markdown Tables")}** {_("support")}
        - **{_("Mermaid Diagrams")}** {_("rendering")}
        - **{_("LaTeX Math")}** {_("equations")}
        - **{_("GitHub Alerts")}**
        - **{_("File History")}** {_("with tags")}
        
        > [!NOTE]
        > {_("This is a GitHub-style note alert!")}
        
        {_("Start editing to see the preview!")}"""

            self.sidebar_widget.set_text(initial_text)
            self._render_markdown_async(initial_text)
        else:
            text = self.sidebar_widget.get_text()
            self._render_markdown_async(text)

        # Connect to text buffer changes with debouncing
        def on_text_update(text):
            self.is_typing = True
            self._debounced_render(text)
            self.content_modified = True
            self._update_title()

            if self.current_file:
                self.file_history.add_file(self.current_file, "edited")

            if self._typing_debounce_id:
                GLib.source_remove(self._typing_debounce_id)
            self._typing_debounce_id = GLib.timeout_add(300, self._reset_typing_state)

        self.sidebar_widget.connect_text_changed(on_text_update)

        self.sidebar_widget.connect_hide_webview(self._on_hide_webview)

        self._setup_bidirectional_scroll_sync()

        # Show sidebar by default on desktop
        sidebar_visible = self.state_manager.is_sidebar_visible()
        self.adw_overlay_split_view.set_show_sidebar(sidebar_visible)

        self.adw_multi_layout_view.connect(
            "notify::layout-name", self._on_layout_changed
        )

        self._on_layout_changed(self.adw_multi_layout_view, None)

        self._update_title()

        self._update_sync_scroll_button()

        self.connect("close-request", self._on_close_request)

        GLib.timeout_add_seconds(30, self._auto_save_state)

    def _on_theme_changed(self, style_manager, param):
        current_text = self.sidebar_widget.get_text()
        html = comrak.render_markdown(
            current_text, extension_options=comrak.ExtensionOptions()
        )
        self.webview_widget.load_html(html, is_dark=self.is_dark_mode())

        self.sidebar_widget._apply_theme(self.is_dark_mode())

    def _reset_typing_state(self):
        """Reset typing state after idle period, resuming sync."""
        self.is_typing = False
        self._typing_debounce_id = None

        return False

    def _setup_bidirectional_scroll_sync(self):
        self._last_sidebar_percentage = 0.0
        self._last_webview_percentage = 0.0
        self._scroll_lock = False

        def on_sidebar_scroll(percentage):
            if not self.sync_scroll_enabled or self.is_typing or self._scroll_lock:
                return

            if abs(percentage - self._last_sidebar_percentage) > 0.005:
                self._last_sidebar_percentage = percentage
                self._scroll_lock = True

                # Scroll webview
                self.webview_widget.scroll_to_percentage(percentage)

                # Reset lock
                GLib.timeout_add(100, lambda: setattr(self, "_scroll_lock", False))

        self.sidebar_widget.connect_scroll_changed(on_sidebar_scroll)

        def on_webview_scroll(percentage):
            if not self.sync_scroll_enabled or self.is_typing or self._scroll_lock:
                return

            if abs(percentage - self._last_webview_percentage) > 0.005:
                self._last_webview_percentage = percentage
                self._scroll_lock = True

                self.sidebar_widget.scroll_to_percentage(percentage)

                GLib.timeout_add(100, lambda: setattr(self, "_scroll_lock", False))

        self.webview_widget.connect_scroll_changed(on_webview_scroll)

    def _on_toggle_sync_scroll(self, button):
        """Toggle scroll synchronization."""
        self.sync_scroll_enabled = not self.sync_scroll_enabled

        self.sidebar_widget.set_sync_scroll_enabled(self.sync_scroll_enabled)
        self.webview_widget.set_sync_scroll_enabled(self.sync_scroll_enabled)

        self.state_manager.state["sync_scroll_enabled"] = self.sync_scroll_enabled
        self.state_manager.save_state()

        self._update_sync_scroll_button()

    def _update_sync_scroll_button(self):
        """Update sync scroll button appearance."""
        if self.sync_scroll_enabled:
            self.toggle_sync_scroll_btn.set_icon_name("view-dual-symbolic")
            self.toggle_sync_scroll_btn.set_tooltip_text(_("Sync Scroll Enabled"))
            self.toggle_sync_scroll_btn.remove_css_class("dim-label")
        else:
            self.toggle_sync_scroll_btn.set_icon_name("view-paged-symbolic")
            self.toggle_sync_scroll_btn.set_tooltip_text(_("Sync Scroll Disabled"))
            self.toggle_sync_scroll_btn.add_css_class("dim-label")

    def _debounced_render(self, text):
        """Debounce text rendering to avoid excessive updates."""
        self._pending_text = text

        if self._update_timer_id:
            GLib.source_remove(self._update_timer_id)

        self._update_timer_id = GLib.timeout_add(100, self._process_pending_text)

    def _process_pending_text(self):
        """Process pending text after debounce period."""
        if self._pending_text is not None:
            self._render_markdown_async(self._pending_text)
            self._pending_text = None
        self._update_timer_id = None
        return False

    def _render_markdown_async(self, text):
        """Render markdown in background thread."""

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
        # New window action (Ctrl+Shift+N)
        new_window_action = Gio.SimpleAction.new("new-window", None)
        new_window_action.connect("activate", self._on_new_window)
        self.add_action(new_window_action)

        # New file action (Ctrl+N)
        new_action = Gio.SimpleAction.new("new-file", None)
        new_action.connect("activate", self._on_new_file)
        self.add_action(new_action)

        # Open file action (Ctrl+O)
        open_action = Gio.SimpleAction.new("open-file", None)
        open_action.connect("activate", self._on_open_file)
        self.add_action(open_action)

        # Open file in new window action
        open_new_window_action = Gio.SimpleAction.new("open-in-new-window", None)
        open_new_window_action.connect("activate", self._on_open_in_new_window)
        self.add_action(open_new_window_action)

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

    def _on_new_window(self, action, param):
        """Open a new window."""
        app = self.get_application()
        if app:
            app._open_new_window()

    def _on_open_in_new_window(self, action, param):
        """Open file in a new window."""
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Open in New Window"))

        filter_md = Gtk.FileFilter()
        filter_md.set_name(_("Markdown Files"))
        filter_md.add_pattern("*.md")
        filter_md.add_pattern("*.markdown")
        filter_md.add_pattern("*.txt")

        filter_all = Gtk.FileFilter()
        filter_all.set_name(_("All Files"))
        filter_all.add_pattern("*")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_md)
        filters.append(filter_all)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_open_in_new_window_response)

    def _on_open_in_new_window_response(self, dialog, result):
        """Handle open in new window response."""
        try:
            file = dialog.open_finish(result)
            if file:
                filepath = file.get_path()
                app = self.get_application()
                if app:
                    app._open_new_window(filepath)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"Error opening file in new window: {e}")

    def _on_new_file(self, action, param):
        """Create new file and track in history."""
        if self.content_modified:
            dialog = Adw.MessageDialog.new(self)
            dialog.set_heading(_("Save Changes?"))
            dialog.set_body(
                _("The document has unsaved changes. Do you want to save them?")
            )
            dialog.add_response("discard", _("Discard"))
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("save", _("Save"))
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
        dialog.set_title(_("Open Markdown File"))

        filter_md = Gtk.FileFilter()
        filter_md.set_name(_("Markdown Files"))
        filter_md.add_pattern("*.md")
        filter_md.add_pattern("*.markdown")
        filter_md.add_pattern("*.txt")

        filter_all = Gtk.FileFilter()
        filter_all.set_name(_("All Files"))
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
        dialog.set_title(_("Save Markdown File"))

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

    def _restore_state(self):
        """Restore application state."""

        window_state = self.state_manager.get_window_state()
        self.set_default_size(
            window_state.get("width", 950), window_state.get("height", 700)
        )

        if window_state.get("maximized", False):
            self.maximize()

        content = self.state_manager.get_content()
        if content:
            self.sidebar_widget.set_text(content)
            cursor_pos = self.state_manager.get_cursor_position()
            try:
                self.sidebar_widget.set_cursor_position(cursor_pos)
            except Exception:
                # If sidebar doesn't expose set_cursor_position, ignore
                pass

        self.current_file = self.state_manager.get_current_file()

        self.webview_hidden = self.state_manager.is_webview_hidden()

        self.sync_scroll_enabled = self.state_manager.state.get(
            "sync_scroll_enabled", True
        )
        self.sidebar_widget.set_sync_scroll_enabled(self.sync_scroll_enabled)
        self.webview_widget.set_sync_scroll_enabled(self.sync_scroll_enabled)

        if self.webview_hidden:
            GLib.idle_add(self._apply_webview_hidden_state)

        self.content_modified = False

        scroll_positions = self.state_manager.get_scroll_positions()
        saved_sidebar_scroll = scroll_positions.get("sidebar", 0.0)
        saved_webview_scroll = scroll_positions.get("webview", 0.0)

        def restore_scrolls():
            # Restore Sidebar scroll
            try:
                self.sidebar_widget.scroll_to_percentage(saved_sidebar_scroll)
            except Exception as e:
                print("Sidebar scroll restore error:", e)

            # WebView needs delay for HTML layout
            def later():
                try:
                    self.webview_widget.scroll_to_percentage(saved_webview_scroll)
                except Exception as e:
                    print("WebView scroll restore error:", e)
                return False

            GLib.timeout_add(350, later)
            return False

        GLib.idle_add(restore_scrolls)

    def _on_about_activate(self, action, param):
        about = Adw.AboutDialog.new()
        about.set_application_name("ProPad")
        about.set_application_icon("io.github.sanjai.ProPad")
        about.set_developer_name("ProPad Team")
        about.set_version("2.0.0")
        about.set_website("https://github.com/Sanjai-Shaarugesh/propad")
        about.set_issue_url("https://github.com/Sanjai-Shaarugesh/propad/issues")
        about.set_copyright("© 2024 ProPad Team")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_developers(["ProPad Contributors", "Built by Sanjai Shaarugesh"])
        about.set_comments(
            "A modern Markdown editor with live preview, "
            "GPU-accelerated rendering, synchronized scrolling, "
            "file history tracking, and support for tables, "
            "Mermaid diagrams, LaTeX math, and GitHub alerts."
        )

        about.add_link("💝 Support Development", "support://show")

        def on_activate_link(dialog, uri):
            if uri == "support://show":
                self._show_support_dialog()
                return True
            return False

        about.connect("activate-link", on_activate_link)
        about.present(self)

    def _show_support_dialog(self):
        dialog = Adw.Window()
        dialog.set_title(_("Support ProPad"))
        dialog.set_default_size(450, 600)
        dialog.set_modal(True)
        dialog.set_transient_for(self)

        toolbar_view = Adw.ToolbarView()

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)

        close_btn = Gtk.Button()
        close_btn.set_icon_name("window-close-symbolic")
        close_btn.connect("clicked", lambda btn: dialog.close())
        header.pack_end(close_btn)

        toolbar_view.add_top_bar(header)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_top(30)
        content_box.set_margin_bottom(30)
        content_box.set_margin_start(30)
        content_box.set_margin_end(30)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)

        title_label = Gtk.Label()
        title_label.set_markup(
            "<span size='xx-large' weight='bold'>☕ Support ProPad</span>"
        )
        title_label.set_halign(Gtk.Align.CENTER)
        content_box.append(title_label)

        desc_label = Gtk.Label()
        desc_label.set_text(
            "If you enjoy using ProPad, consider buying me a coffee!\n"
            "Your support helps keep the project alive."
        )
        desc_label.set_justify(Gtk.Justification.CENTER)
        desc_label.set_wrap(True)
        desc_label.set_halign(Gtk.Align.CENTER)
        desc_label.add_css_class("dim-label")
        content_box.append(desc_label)

        qr_image_path = "data/images/buymeacoffee-qr.png"
        if os.path.exists(qr_image_path):
            qr_frame = Gtk.Frame()
            qr_frame.set_halign(Gtk.Align.CENTER)

            qr_image = Gtk.Picture.new_for_filename(qr_image_path)
            qr_image.set_size_request(200, 200)
            qr_image.set_halign(Gtk.Align.CENTER)
            qr_image.set_valign(Gtk.Align.CENTER)

            qr_frame.set_child(qr_image)
            content_box.append(qr_frame)

            qr_label = Gtk.Label()
            qr_label.set_text("Scan with your phone")
            qr_label.add_css_class("dim-label")
            qr_label.set_halign(Gtk.Align.CENTER)
            content_box.append(qr_label)
        else:
            placeholder = Gtk.Label()
            placeholder.set_markup(
                "<span size='xx-large'>📱</span>\n"
                "<small>Place QR code at:\ndata/images/buymeacoffee-qr.png</small>"
            )
            placeholder.set_justify(Gtk.Justification.CENTER)
            placeholder.set_halign(Gtk.Align.CENTER)
            content_box.append(placeholder)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(10)
        separator.set_margin_bottom(10)
        content_box.append(separator)

        button_image_path = "data/images/buymeacoffee-button.png"
        if os.path.exists(button_image_path):
            # Use image button
            image_button = Gtk.Button()
            button_image = Gtk.Picture.new_for_filename(button_image_path)
            button_image.set_size_request(170, 50)
            image_button.set_child(button_image)
            image_button.add_css_class("flat")
            image_button.set_halign(Gtk.Align.CENTER)
            image_button.connect(
                "clicked",
                lambda btn: Gtk.show_uri(self, "https://buymeacoffee.com/sanjai", 0),
            )
            content_box.append(image_button)
        else:
            coffee_button = Gtk.Button()
            coffee_button.set_label("☕ Open Buy Me a Coffee")
            coffee_button.add_css_class("pill")
            coffee_button.add_css_class("suggested-action")
            coffee_button.set_halign(Gtk.Align.CENTER)
            coffee_button.set_size_request(250, -1)
            coffee_button.connect(
                "clicked",
                lambda btn: Gtk.show_uri(self, "https://buymeacoffee.com/sanjai", 0),
            )
            content_box.append(coffee_button)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(content_box)

        toolbar_view.set_content(scrolled)
        dialog.set_content(toolbar_view)
        dialog.present()

    def load_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.sidebar_widget.set_text(content)
            self.current_file = filepath
            self.content_modified = False
            self._update_title()
            self.state_manager.save_current_file(filepath)

            self.file_history.add_file(filepath, "opened")

        except Exception as e:
            print(f"❌ Error loading file: {e}")

    def _apply_webview_hidden_state(self):
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
        self._save_state()
        return True

    def _save_state(self):
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

        # Save scroll positions before exit
        self.sidebar_widget.get_scroll_percentage(
            lambda sidebar_pos: self.webview_widget.get_scroll_percentage(
                lambda webview_pos: self.state_manager.save_scroll_positions(
                    sidebar_pos, webview_pos
                )
            )
        )

        # Save rest of the state
        self._save_state()
        time.sleep(0.1)
        return False

    def _update_title(self):
        if self.current_file:
            filename = os.path.basename(self.current_file)
            if self.content_modified:
                self.set_title(f"● {filename} - {_('ProPad')}")
            else:
                self.set_title(f"{filename} - {_('ProPad')}")
        else:
            if self.content_modified:
                self.set_title(f"● {_('Untitled')} - {_('ProPad')}")
            else:
                self.set_title(_("ProPad"))

    def set_current_file(self, filepath):
        self.current_file = filepath
        self.content_modified = False
        self._update_title()
        self.state_manager.save_current_file(filepath)

    def mark_content_modified(self, modified: bool = True):
        self.content_modified = modified
        self._update_title()

    def is_dark_mode(self) -> bool:
        style_manager = Adw.StyleManager.get_default()
        return style_manager.get_dark()

    def _on_toggle_sidebar(self, button: Gtk.Button) -> None:
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
