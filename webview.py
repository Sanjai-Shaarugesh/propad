import gi

gi.require_version(namespace="Gtk", version="4.0")
gi.require_version(namespace="WebKit", version="6.0")

from gi.repository import Gtk, WebKit
from typing import Optional

UI_FILE = "ui/webview.ui"


@Gtk.Template(filename=UI_FILE)
class WebViewWidget(Gtk.Box):
    __gtype_name__ = "WebViewWidget"

    webview_container = Gtk.Template.Child()

    def __init__(self, **kwargs):
        if "orientation" not in kwargs:
            kwargs["orientation"] = Gtk.Orientation.VERTICAL
        super().__init__(**kwargs)

        # Create WebView
        self.webview = WebKit.WebView.new()

        # Configure settings
        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_webgl(True)
        settings.set_enable_html5_database(True)
        settings.set_enable_html5_local_storage(True)

        # Set expand properties
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)

        # Add to container
        self.webview_container.append(self.webview)

        # Connect signals
        self.webview.connect("load-changed", self._on_load_changed)

    def load_uri(self, uri: str) -> None:
        """Load a URI in the webview."""
        self.webview.load_uri(uri)

    def load_html(self, html: str, base_uri: Optional[str] = None) -> None:
        """Load HTML content in the webview."""
        self.webview.load_html(html, base_uri)

    def reload(self) -> None:
        """Reload the current page."""
        self.webview.reload()

    def go_back(self) -> None:
        """Go back in history."""
        if self.webview.can_go_back():
            self.webview.go_back()

    def go_forward(self) -> None:
        """Go forward in history."""
        if self.webview.can_go_forward():
            self.webview.go_forward()

    def get_uri(self) -> Optional[str]:
        """Get the current URI."""
        return self.webview.get_uri()

    def _on_load_changed(
        self, webview: WebKit.WebView, load_event: WebKit.LoadEvent
    ) -> None:
        """Handle load state changes."""
        if load_event == WebKit.LoadEvent.FINISHED:
            uri = self.get_uri()
            if uri:
                print(f"Page loaded: {uri}")
