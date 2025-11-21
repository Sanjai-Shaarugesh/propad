import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, WebKit, Adw
from typing import Optional
import comrak

UI_FILE = "ui/webview.ui"


@Gtk.Template(filename=UI_FILE)
class WebViewWidget(Gtk.Box):
    __gtype_name__ = "WebViewWidget"

    webview_container = Gtk.Template.Child()

    def __init__(self, **kwargs):
        if "orientation" not in kwargs:
            kwargs["orientation"] = Gtk.Orientation.VERTICAL
        super().__init__(**kwargs)

        self.webview = WebKit.WebView.new()
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)
        self.webview_container.append(self.webview)

        self._last_html = ""
        self._last_is_dark = None

        self.webview.load_html("<p></p>", "file:///")  # Load empty content

        # Listen to Adw.StyleManager for theme changes
        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", self._on_theme_changed)

        # Apply theme immediately
        self.set_theme(self.is_dark_mode())

    def _on_theme_changed(self, style_manager, param):
        """Reload content with new theme when system theme changes."""
        is_dark = style_manager.get_dark()
        if self._last_html and is_dark != self._last_is_dark:
            self.load_html(self._last_html, is_dark=is_dark)

    def is_dark_mode(self) -> bool:
        """Check if the current theme is dark using Adw.StyleManager."""
        style_manager = Adw.StyleManager.get_default()
        return style_manager.get_dark()

    def set_theme(self, is_dark: bool):
        """Inject CSS instantly without reloading."""
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#d4d4d4" if is_dark else "#1e1e1e"
        link_color = "#4fc3f7" if is_dark else "#0066cc"
        code_bg = "#2d2d2d" if is_dark else "#f5f5f5"
        pre_bg = "#2d2d2d" if is_dark else "#f5f5f5"

        js_code = f"""
        let style = document.getElementById('theme-style');
        if (!style) {{
            style = document.createElement('style');
            style.id = 'theme-style';
            document.head.appendChild(style);
        }}
        style.innerHTML = `
            body {{ background: {bg_color}; color: {text_color}; transition: background 0.2s, color 0.2s; }}
            a {{ color: {link_color}; }}
            code {{ background: {code_bg}; }}
            pre {{ background: {pre_bg}; }}
        `;
        """
        self.webview.evaluate_javascript(js_code, -1, None, None, None)

    def load_html(self, html: str, is_dark: Optional[bool] = None):
        """Load HTML content and apply the theme immediately."""
        if is_dark is None:
            is_dark = self.is_dark_mode()

        # Store the HTML content and theme state
        self._last_html = html
        self._last_is_dark = is_dark

        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#d4d4d4" if is_dark else "#1e1e1e"
        link_color = "#4fc3f7" if is_dark else "#0066cc"
        code_bg = "#2d2d2d" if is_dark else "#f5f5f5"
        pre_bg = "#2d2d2d" if is_dark else "#f5f5f5"

        html_content = f"""<!DOCTYPE html>
    <html>
    <head>
    <style id="theme-style">
    body {{ background: {bg_color}; color: {text_color}; font-family: sans-serif; padding: 20px; }}
    a {{ color: {link_color}; }}
    code {{ background: {code_bg}; padding: 2px 4px; border-radius: 3px; }}
    pre {{ background: {pre_bg}; padding: 10px; border-radius: 5px; overflow-x: auto; }}
    pre code {{ background: none; padding: 0; }}
    </style>
    </head>
    <body>
    {html}
    </body>
    </html>"""

        self.webview.load_html(html_content, "file:///")

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
