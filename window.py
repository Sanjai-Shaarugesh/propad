import gi

gi.require_version(namespace="Gtk", version="4.0")
gi.require_version(namespace="Adw", version="1")

from gi.repository import Adw, Gtk
from sidebar import SidebarWidget
from webview import WebViewWidget

UI_FILE = "ui/window.ui"


@Gtk.Template(filename=UI_FILE)
class Window(Adw.ApplicationWindow):
    __gtype_name__ = "Window"

    toggle_sidebar_btn = Gtk.Template.Child()
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

        # Connect sidebar toggle button
        self.toggle_sidebar_btn.connect("clicked", self._on_toggle_sidebar)

        # Create widgets
        self.sidebar_widget = SidebarWidget()
        self.webview_widget = WebViewWidget()
        self.webview_widget.load_uri("https://www.example.com")

        # Add to desktop view initially
        self.sidebar_container.append(self.sidebar_widget)
        self.webview_container.append(self.webview_widget)

        # Show sidebar by default on desktop
        self.adw_overlay_split_view.set_show_sidebar(True)

        # Listen for layout changes
        self.adw_multi_layout_view.connect(
            "notify::layout-name", self._on_layout_changed
        )

        # Set initial layout
        self._on_layout_changed(self.adw_multi_layout_view, None)

    def _on_toggle_sidebar(self, button: Gtk.Button) -> None:
        """Toggle sidebar visibility."""
        self.adw_overlay_split_view.set_show_sidebar(
            not self.adw_overlay_split_view.get_show_sidebar()
        )

    def _on_layout_changed(self, multi_layout: Adw.MultiLayoutView, _) -> None:
        """Handle layout changes between desktop and mobile."""
        layout_name = multi_layout.get_layout_name()

        if layout_name == "mobile" and not self.is_mobile:
            self._switch_to_mobile()
        elif layout_name == "desktop" and self.is_mobile:
            self._switch_to_desktop()

    def _switch_to_mobile(self) -> None:
        """Switch to mobile layout."""
        print("Switching to mobile layout")
        self.is_mobile = True

        # Remove from desktop containers
        parent = self.sidebar_widget.get_parent()
        if parent:
            parent.remove(self.sidebar_widget)

        parent = self.webview_widget.get_parent()
        if parent:
            parent.remove(self.webview_widget)

        # Add to mobile containers
        self.mobile_sidebar_container.append(self.sidebar_widget)
        self.mobile_webview_container.append(self.webview_widget)

    def _switch_to_desktop(self) -> None:
        """Switch to desktop layout."""
        print("Switching to desktop layout")
        self.is_mobile = False

        # Remove from mobile containers
        parent = self.sidebar_widget.get_parent()
        if parent:
            parent.remove(self.sidebar_widget)

        parent = self.webview_widget.get_parent()
        if parent:
            parent.remove(self.webview_widget)

        # Add back to desktop containers
        self.sidebar_container.append(self.sidebar_widget)
        self.webview_container.append(self.webview_widget)

        # Show sidebar on desktop
        self.adw_overlay_split_view.set_show_sidebar(True)

    def get_sidebar(self) -> SidebarWidget:
        """Get the sidebar widget."""
        return self.sidebar_widget

    def get_webview(self) -> WebViewWidget:
        """Get the webview widget."""
        return self.webview_widget
