import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, WebKit, Adw
from typing import Optional
import comrak
import re
import os

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

        # Connect to decide-policy signal to handle link clicks
        self.webview.connect("decide-policy", self._on_decide_policy)

        # Connect to context-menu signal to handle right-click actions
        self.webview.connect("context-menu", self._on_context_menu)

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

    def _on_decide_policy(self, webview, decision, decision_type):
        """Handle navigation decisions - open external links in browser."""
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            nav_action = decision.get_navigation_action()
            request = nav_action.get_request()
            uri = request.get_uri()

            # Allow file:// URIs (our local content)
            if uri and uri.startswith("file://"):
                decision.use()
                return False

            # Open external links (http://, https://) in default browser
            if uri and (uri.startswith("http://") or uri.startswith("https://")):
                print(f"Opening external link: {uri}")
                Gtk.show_uri(None, uri, 0)
                decision.ignore()
                return True

            # Allow other URIs to be handled by WebView
            decision.use()
            return False

        return False

    def _on_context_menu(self, webview, context_menu, hit_test_result):
        """Handle context menu - customize to open links in external browser."""
        # Get the items in the context menu
        items = context_menu.get_items()

        # Remove reload and other navigation items
        for item in list(items):
            action = item.get_stock_action()
            if action in [
                WebKit.ContextMenuAction.RELOAD,
                WebKit.ContextMenuAction.GO_BACK,
                WebKit.ContextMenuAction.GO_FORWARD,
                WebKit.ContextMenuAction.STOP,
            ]:
                context_menu.remove(item)

        # Check if we're on a link
        if hit_test_result.context_is_link():
            link_uri = hit_test_result.get_link_uri()

            # Remove all default link-related items
            for item in list(
                items
            ):  # Convert to list to avoid modification during iteration
                action = item.get_stock_action()
                # Remove: Open Link, Open Link in New Window, Download Linked File, Copy Link
                if action in [
                    WebKit.ContextMenuAction.OPEN_LINK,
                    WebKit.ContextMenuAction.OPEN_LINK_IN_NEW_WINDOW,
                    WebKit.ContextMenuAction.DOWNLOAD_LINK_TO_DISK,
                    WebKit.ContextMenuAction.COPY_LINK_TO_CLIPBOARD,
                ]:
                    context_menu.remove(item)

            # Add custom "Open Link in Browser" action at the top
            if link_uri and (
                link_uri.startswith("http://") or link_uri.startswith("https://")
            ):
                # Create a custom action using Gio.SimpleAction
                from gi.repository import Gio

                action = Gio.SimpleAction.new("open-in-browser", None)
                action.connect("activate", lambda a, p: Gtk.show_uri(None, link_uri, 0))

                open_action = WebKit.ContextMenuItem.new_from_gaction(
                    action, "Open Link in Browser", None
                )
                context_menu.prepend(open_action)

                # Add "Copy Link" action
                copy_action_obj = Gio.SimpleAction.new("copy-link", None)
                copy_action_obj.connect(
                    "activate", lambda a, p: self._copy_to_clipboard(link_uri)
                )

                copy_action = WebKit.ContextMenuItem.new_from_gaction(
                    copy_action_obj, "Copy Link", None
                )
                context_menu.append(copy_action)

        # Check if we're on an image
        if hit_test_result.context_is_image():
            image_uri = hit_test_result.get_image_uri()

            # Remove default image actions and add custom ones
            for item in list(
                items
            ):  # Convert to list to avoid modification during iteration
                action = item.get_stock_action()
                if action in [
                    WebKit.ContextMenuAction.OPEN_IMAGE_IN_NEW_WINDOW,
                    WebKit.ContextMenuAction.DOWNLOAD_IMAGE_TO_DISK,
                ]:
                    context_menu.remove(item)

            # Add custom "Open Image in Browser" if it's an external image
            if image_uri and (
                image_uri.startswith("http://") or image_uri.startswith("https://")
            ):
                from gi.repository import Gio

                img_action = Gio.SimpleAction.new("open-image-in-browser", None)
                img_action.connect(
                    "activate", lambda a, p: Gtk.show_uri(None, image_uri, 0)
                )

                open_img_action = WebKit.ContextMenuItem.new_from_gaction(
                    img_action, "Open Image in Browser", None
                )
                context_menu.append(open_img_action)

        return False

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        clipboard = self.get_clipboard()
        clipboard.set(text)

    def is_dark_mode(self) -> bool:
        """Check if the current theme is dark using Adw.StyleManager."""
        style_manager = Adw.StyleManager.get_default()
        return style_manager.get_dark()

    def _process_github_alerts(self, html: str) -> str:
        """Convert GitHub-style alerts/admonitions to styled divs."""
        # Pattern for blockquotes that start with [!NOTE], [!TIP], etc.
        alert_pattern = re.compile(
            r"<blockquote>\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*?)</p>(.*?)</blockquote>",
            re.DOTALL | re.IGNORECASE,
        )

        def replace_alert(match):
            alert_type = match.group(1).upper()
            first_line = match.group(2).strip()
            rest_content = match.group(3).strip()

            # Combine first line with rest of content
            full_content = first_line
            if rest_content:
                full_content += rest_content

            return f'<div class="alert alert-{alert_type.lower()}" data-alert-type="{alert_type}">{full_content}</div>'

        return alert_pattern.sub(replace_alert, html)

    def _process_mermaid_blocks(self, html: str) -> str:
        """Convert mermaid code blocks to mermaid divs."""
        # Try multiple patterns to catch different markdown renderers
        patterns = [
            # Pattern 1: <pre><code class="language-mermaid">...</code></pre>
            re.compile(
                r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.DOTALL
            ),
            # Pattern 2: <pre lang="mermaid"><code>...</code></pre>
            re.compile(r'<pre lang="mermaid"><code>(.*?)</code></pre>', re.DOTALL),
            # Pattern 3: <code class="language-mermaid">...</code> without pre
            re.compile(r'<code class="language-mermaid">(.*?)</code>', re.DOTALL),
            # Pattern 4: Just looking for ```mermaid in plain text (fallback)
            re.compile(r"```mermaid\s*(.*?)\s*```", re.DOTALL),
        ]

        def replace_mermaid(match):
            mermaid_code = match.group(1).strip()
            # Unescape HTML entities that might be in the code
            mermaid_code = (
                mermaid_code.replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
                .replace("&quot;", '"')
            )
            return f'<div class="mermaid">\n{mermaid_code}\n</div>'

        # Apply all patterns in sequence
        result = html
        for pattern in patterns:
            result = pattern.sub(replace_mermaid, result)

        return result

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

    def _load_external_file(self, filename: str) -> str:
        """Load content from an external file."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return ""

    def load_html(self, html: str, is_dark: Optional[bool] = None):
        """Load HTML content and apply the theme immediately."""
        if is_dark is None:
            is_dark = self.is_dark_mode()

        # Store the ORIGINAL HTML content and theme state (before processing)
        self._last_html = html
        self._last_is_dark = is_dark

        # Debug: Check if mermaid code exists in input
        if "mermaid" in html.lower():
            print(f"DEBUG: Found mermaid in HTML (length: {len(html)})")

        # Process Mermaid blocks FIRST (before GitHub alerts)
        processed_html = self._process_mermaid_blocks(html)

        # Debug: Check if conversion happened
        if (
            'class="mermaid"' in processed_html
            or '<div class="mermaid">' in processed_html
        ):
            print("DEBUG: Successfully converted to mermaid div")

        # Process GitHub-style alerts
        processed_html = self._process_github_alerts(processed_html)

        # Load external CSS and JS files
        css_content = self._load_external_file("assets/styles.css")
        js_mermaid = self._load_external_file("assets/mermaid-loader.js")
        js_mathjax_config = self._load_external_file("assets/mathjax-config.js")
        js_mathjax_render = self._load_external_file("assets/mathjax-render.js")

        # Get theme colors
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#d4d4d4" if is_dark else "#1e1e1e"
        link_color = "#4fc3f7" if is_dark else "#0066cc"
        code_bg = "#2d2d2d" if is_dark else "#f5f5f5"
        pre_bg = "#2d2d2d" if is_dark else "#f5f5f5"
        border_color = "#333333" if is_dark else "#e1e4e8"
        mermaid_theme = "dark" if is_dark else "default"

        # Alert colors (GitHub-style)
        if is_dark:
            note_bg = "#1f2937"
            note_border = "#3b82f6"
            note_icon = "#3b82f6"

            tip_bg = "#1e3a2e"
            tip_border = "#10b981"
            tip_icon = "#10b981"

            important_bg = "#3a2e42"
            important_border = "#a855f7"
            important_icon = "#a855f7"

            warning_bg = "#3a2e1e"
            warning_border = "#f59e0b"
            warning_icon = "#f59e0b"

            caution_bg = "#3a1e1e"
            caution_border = "#ef4444"
            caution_icon = "#ef4444"
        else:
            note_bg = "#dbeafe"
            note_border = "#3b82f6"
            note_icon = "#1e40af"

            tip_bg = "#d1fae5"
            tip_border = "#10b981"
            tip_icon = "#065f46"

            important_bg = "#f3e8ff"
            important_border = "#a855f7"
            important_icon = "#6b21a8"

            warning_bg = "#fef3c7"
            warning_border = "#f59e0b"
            warning_icon = "#92400e"

            caution_bg = "#fee2e2"
            caution_border = "#ef4444"
            caution_icon = "#991b1b"

        # Replace CSS variables with actual values
        css_with_theme = (
            css_content.replace("{bg_color}", bg_color)
            .replace("{text_color}", text_color)
            .replace("{link_color}", link_color)
            .replace("{code_bg}", code_bg)
            .replace("{pre_bg}", pre_bg)
            .replace("{border_color}", border_color)
            .replace("{note_bg}", note_bg)
            .replace("{note_border}", note_border)
            .replace("{note_icon}", note_icon)
            .replace("{tip_bg}", tip_bg)
            .replace("{tip_border}", tip_border)
            .replace("{tip_icon}", tip_icon)
            .replace("{important_bg}", important_bg)
            .replace("{important_border}", important_border)
            .replace("{important_icon}", important_icon)
            .replace("{warning_bg}", warning_bg)
            .replace("{warning_border}", warning_border)
            .replace("{warning_icon}", warning_icon)
            .replace("{caution_bg}", caution_bg)
            .replace("{caution_border}", caution_border)
            .replace("{caution_icon}", caution_icon)
        )

        # Replace JS variables with actual values
        js_mermaid_with_theme = js_mermaid.replace("{mermaid_theme}", mermaid_theme)

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style id="theme-style">
{css_with_theme}
</style>

<!-- Mermaid for diagrams (Latest Version v11) - Load FIRST -->
<script type="module">
{js_mermaid_with_theme}
</script>

<!-- MathJax for LaTeX (Full Support) -->
<script>
{js_mathjax_config}
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<!-- Ensure MathJax renders after page load -->
<script>
{js_mathjax_render}
</script>
</head>
<body>
{processed_html}
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
