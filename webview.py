import gi
import threading
from concurrent.futures import ThreadPoolExecutor
import os

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, WebKit, Adw, GLib, Gdk
from typing import Optional
import comrak
import re

UI_FILE = "ui/webview.ui"


@Gtk.Template(filename=UI_FILE)
class WebViewWidget(Gtk.Box):
    __gtype_name__ = "WebViewWidget"

    webview_container = Gtk.Template.Child()

    def __init__(self, **kwargs):
        if "orientation" not in kwargs:
            kwargs["orientation"] = Gtk.Orientation.VERTICAL
        super().__init__(**kwargs)

        # Thread pool for parallel processing
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

        # Cache for processed content and loaded files
        self._file_cache = {}
        self._html_cache = {}

        # Sync scroll state
        self.sync_scroll_enabled = True
        self._is_programmatic_scroll = False
        self._scroll_sync_handler_id = None

        # Pre-load external files in background
        self._preload_external_files()

        # Create WebView with GPU acceleration
        settings = WebKit.Settings()
        settings.set_enable_webgl(True)
        settings.set_enable_webaudio(True)
        settings.set_hardware_acceleration_policy(
            WebKit.HardwareAccelerationPolicy.ALWAYS
        )
        settings.set_enable_page_cache(True)
        settings.set_enable_javascript(True)
        settings.set_enable_smooth_scrolling(True)
        settings.set_javascript_can_access_clipboard(True)

        self.webview = WebKit.WebView()
        self.webview.set_settings(settings)
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)

        # Enable GPU compositing
        try:
            self.webview.set_background_color(Gdk.RGBA(1, 1, 1, 1))
        except:
            pass

        self.webview_container.append(self.webview)

        self._last_html = ""
        self._last_is_dark = None
        self._rendering_lock = threading.Lock()

        # Connect to decide-policy signal to handle link clicks
        self.webview.connect("decide-policy", self._on_decide_policy)

        # Connect to context-menu signal to handle right-click actions
        self.webview.connect("context-menu", self._on_context_menu)

        self.webview.load_html("<p></p>", "file:///")

        # Listen to Adw.StyleManager for theme changes
        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", self._on_theme_changed)

        # Apply theme immediately
        self.set_theme(self.is_dark_mode())

    def _preload_external_files(self):
        """Pre-load external files in background thread for faster access."""

        def load_files():
            files_to_load = [
                "assets/styles.css",
                "assets/mermaid-loader.js",
                "assets/mathjax-config.js",
                "assets/mathjax-render.js",
            ]
            for filename in files_to_load:
                if filename not in self._file_cache:
                    self._file_cache[filename] = self._load_external_file(filename)

        # Load in background
        self._thread_pool.submit(load_files)

    def set_sync_scroll_enabled(self, enabled: bool):
        """Enable or disable synchronized scrolling."""
        self.sync_scroll_enabled = enabled

    def scroll_to_percentage(self, percentage: float):
        """Scroll webview to a specific percentage (0.0 to 1.0)."""
        if not self.sync_scroll_enabled or self._is_programmatic_scroll:
            return

        self._is_programmatic_scroll = True

        js_code = f"""
        (function() {{
            const maxScroll = Math.max(
                document.documentElement.scrollHeight - window.innerHeight,
                0
            );
            const targetScroll = maxScroll * {percentage};
            window.scrollTo({{
                top: targetScroll,
                behavior: 'auto'
            }});
        }})();
        """

        self.webview.evaluate_javascript(js_code, -1, None, None, None)

        # Reset flag after scroll completes
        GLib.timeout_add(50, lambda: setattr(self, "_is_programmatic_scroll", False))

    def get_scroll_percentage(self, callback):
        """Get current scroll percentage asynchronously."""
        js_code = """
        (function() {
            const maxScroll = Math.max(
                document.documentElement.scrollHeight - window.innerHeight,
                0
            );
            if (maxScroll === 0) return 0;
            return window.scrollY / maxScroll;
        })();
        """

        def on_result(webview, result, user_data):
            try:
                js_result = webview.evaluate_javascript_finish(result)
                if js_result:
                    value = js_result.to_double()
                    callback(value)
            except Exception as e:
                print(f"Error getting scroll percentage: {e}")
                callback(0)

        self.webview.evaluate_javascript(js_code, -1, None, on_result, None)

    def setup_scroll_monitoring(self):
        """Setup scroll event monitoring in the webview."""
        if self._scroll_sync_handler_id:
            return

        js_code = """
        (function() {
            let scrollTimeout;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {
                    const maxScroll = Math.max(
                        document.documentElement.scrollHeight - window.innerHeight,
                        0
                    );
                    const percentage = maxScroll === 0 ? 0 : window.scrollY / maxScroll;
                    
                    // Signal to GTK (stored in window for external access)
                    window.lastScrollPercentage = percentage;
                }, 50);
            });
        })();
        """

        self.webview.evaluate_javascript(js_code, -1, None, None, None)
        self._scroll_sync_handler_id = True

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

            if uri and uri.startswith("file://"):
                decision.use()
                return False

            if uri and (uri.startswith("http://") or uri.startswith("https://")):
                Gtk.show_uri(None, uri, 0)
                decision.ignore()
                return True

            decision.use()
            return False

        return False

    def _on_context_menu(self, webview, context_menu, hit_test_result):
        """Handle context menu - customize to open links in external browser."""
        items = context_menu.get_items()

        for item in list(items):
            action = item.get_stock_action()
            if action in [
                WebKit.ContextMenuAction.RELOAD,
                WebKit.ContextMenuAction.GO_BACK,
                WebKit.ContextMenuAction.GO_FORWARD,
                WebKit.ContextMenuAction.STOP,
            ]:
                context_menu.remove(item)

        if hit_test_result.context_is_link():
            link_uri = hit_test_result.get_link_uri()

            for item in list(items):
                action = item.get_stock_action()
                if action in [
                    WebKit.ContextMenuAction.OPEN_LINK,
                    WebKit.ContextMenuAction.OPEN_LINK_IN_NEW_WINDOW,
                    WebKit.ContextMenuAction.DOWNLOAD_LINK_TO_DISK,
                    WebKit.ContextMenuAction.COPY_LINK_TO_CLIPBOARD,
                ]:
                    context_menu.remove(item)

            if link_uri and (
                link_uri.startswith("http://") or link_uri.startswith("https://")
            ):
                from gi.repository import Gio

                action = Gio.SimpleAction.new("open-in-browser", None)
                action.connect("activate", lambda a, p: Gtk.show_uri(None, link_uri, 0))

                open_action = WebKit.ContextMenuItem.new_from_gaction(
                    action, "Open Link in Browser", None
                )
                context_menu.prepend(open_action)

                copy_action_obj = Gio.SimpleAction.new("copy-link", None)
                copy_action_obj.connect(
                    "activate", lambda a, p: self._copy_to_clipboard(link_uri)
                )

                copy_action = WebKit.ContextMenuItem.new_from_gaction(
                    copy_action_obj, "Copy Link", None
                )
                context_menu.append(copy_action)

        if hit_test_result.context_is_image():
            image_uri = hit_test_result.get_image_uri()

            for item in list(items):
                action = item.get_stock_action()
                if action in [
                    WebKit.ContextMenuAction.OPEN_IMAGE_IN_NEW_WINDOW,
                    WebKit.ContextMenuAction.DOWNLOAD_IMAGE_TO_DISK,
                ]:
                    context_menu.remove(item)

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
        alert_pattern = re.compile(
            r"<blockquote>\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*?)</p>(.*?)</blockquote>",
            re.DOTALL | re.IGNORECASE,
        )

        def replace_alert(match):
            alert_type = match.group(1).upper()
            first_line = match.group(2).strip()
            rest_content = match.group(3).strip()
            full_content = first_line
            if rest_content:
                full_content += rest_content
            return f'<div class="alert alert-{alert_type.lower()}" data-alert-type="{alert_type}">{full_content}</div>'

        return alert_pattern.sub(replace_alert, html)

    def _process_mermaid_blocks(self, html: str) -> str:
        """Convert mermaid code blocks to mermaid divs."""
        patterns = [
            re.compile(
                r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.DOTALL
            ),
            re.compile(r'<pre lang="mermaid"><code>(.*?)</code></pre>', re.DOTALL),
            re.compile(r'<code class="language-mermaid">(.*?)</code>', re.DOTALL),
            re.compile(r"```mermaid\s*(.*?)\s*```", re.DOTALL),
        ]

        def replace_mermaid(match):
            mermaid_code = match.group(1).strip()
            mermaid_code = (
                mermaid_code.replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
                .replace("&quot;", '"')
            )
            return f'<div class="mermaid">\n{mermaid_code}\n</div>'

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
        """Load HTML content with GPU-accelerated rendering in background thread."""
        if is_dark is None:
            is_dark = self.is_dark_mode()

        # Store original HTML
        self._last_html = html
        self._last_is_dark = is_dark

        # Process HTML in background thread
        def process_html_async():
            with self._rendering_lock:
                # Check cache first
                cache_key = (hash(html), is_dark)
                if cache_key in self._html_cache:
                    html_content = self._html_cache[cache_key]
                    GLib.idle_add(lambda: self._finish_load_html(html_content))
                    return

                # Process HTML
                processed_html = self._process_mermaid_blocks(html)
                processed_html = self._process_github_alerts(processed_html)

                # Load external files from cache
                css_content = self._file_cache.get(
                    "assets/styles.css"
                ) or self._load_external_file("assets/styles.css")
                js_mermaid = self._file_cache.get(
                    "assets/mermaid-loader.js"
                ) or self._load_external_file("assets/mermaid-loader.js")
                js_mathjax_config = self._file_cache.get(
                    "assets/mathjax-config.js"
                ) or self._load_external_file("assets/mathjax-config.js")
                js_mathjax_render = self._file_cache.get(
                    "assets/mathjax-render.js"
                ) or self._load_external_file("assets/mathjax-render.js")

                # Get theme colors
                bg_color = "#1e1e1e" if is_dark else "#ffffff"
                text_color = "#d4d4d4" if is_dark else "#1e1e1e"
                link_color = "#4fc3f7" if is_dark else "#0066cc"
                code_bg = "#2d2d2d" if is_dark else "#f5f5f5"
                pre_bg = "#2d2d2d" if is_dark else "#f5f5f5"
                border_color = "#333333" if is_dark else "#e1e4e8"
                mermaid_theme = "dark" if is_dark else "default"

                # Alert colors
                if is_dark:
                    note_bg, note_border, note_icon = "#1f2937", "#3b82f6", "#3b82f6"
                    tip_bg, tip_border, tip_icon = "#1e3a2e", "#10b981", "#10b981"
                    important_bg, important_border, important_icon = (
                        "#3a2e42",
                        "#a855f7",
                        "#a855f7",
                    )
                    warning_bg, warning_border, warning_icon = (
                        "#3a2e1e",
                        "#f59e0b",
                        "#f59e0b",
                    )
                    caution_bg, caution_border, caution_icon = (
                        "#3a1e1e",
                        "#ef4444",
                        "#ef4444",
                    )
                else:
                    note_bg, note_border, note_icon = "#dbeafe", "#3b82f6", "#1e40af"
                    tip_bg, tip_border, tip_icon = "#d1fae5", "#10b981", "#065f46"
                    important_bg, important_border, important_icon = (
                        "#f3e8ff",
                        "#a855f7",
                        "#6b21a8",
                    )
                    warning_bg, warning_border, warning_icon = (
                        "#fef3c7",
                        "#f59e0b",
                        "#92400e",
                    )
                    caution_bg, caution_border, caution_icon = (
                        "#fee2e2",
                        "#ef4444",
                        "#991b1b",
                    )

                # Build HTML with theme
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

                js_mermaid_with_theme = js_mermaid.replace(
                    "{mermaid_theme}", mermaid_theme
                )

                html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style id="theme-style">
{css_with_theme}
</style>

<!-- Mermaid for diagrams (Latest Version v11) -->
<script type="module">
{js_mermaid_with_theme}
</script>

<!-- MathJax for LaTeX -->
<script>
{js_mathjax_config}
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<script>
{js_mathjax_render}
</script>
</head>
<body>
{processed_html}
</body>
</html>"""

                # Cache the result
                self._html_cache[cache_key] = html_content

                # Keep cache size reasonable
                if len(self._html_cache) > 10:
                    self._html_cache.clear()

                # Load in main thread
                GLib.idle_add(lambda: self._finish_load_html(html_content))

        # Process in background thread
        self._thread_pool.submit(process_html_async)

    def _finish_load_html(self, html_content):
        """Finish loading HTML in main thread."""
        self.webview.load_html(html_content, "file:///")
        # Setup scroll monitoring after content loads
        GLib.timeout_add(500, self.setup_scroll_monitoring)

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
