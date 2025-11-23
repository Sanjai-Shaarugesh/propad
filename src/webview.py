import gi
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import time

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, WebKit, Adw, GLib, Gdk
from typing import Optional, Callable
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
        self._thread_pool = ThreadPoolExecutor(max_workers=8)

        # Cache for processed content
        self._file_cache = {}
        self._html_cache = {}
        self._last_theme = None

        # Ultra-smooth scroll state with 120fps support
        self.sync_scroll_enabled = True
        self._is_programmatic_scroll = False
        self._scroll_sync_handler_id = None
        self._target_scroll_percentage = 0.0
        self._current_scroll_percentage = 0.0
        self._scroll_velocity = 0.0

        # Bidirectional scroll callbacks
        self._scroll_callbacks = []

        # Pre-load external files
        self._preload_external_files()

        # Create WebView with maximum GPU acceleration
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
        settings.set_enable_javascript_markup(True)
        settings.set_enable_media(True)
        settings.set_enable_media_capabilities(True)

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
        self._theme_change_pending = False

        # Connect signals
        self.webview.connect("decide-policy", self._on_decide_policy)
        self.webview.connect("context-menu", self._on_context_menu)
        self.webview.load_html("<p></p>", "file:///")

        # Listen to theme changes
        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", self._on_theme_changed)
        self.set_theme(self.is_dark_mode())

    def _preload_external_files(self):
        """Pre-load external files in background."""

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

        self._thread_pool.submit(load_files)

    def set_sync_scroll_enabled(self, enabled: bool):
        """Enable or disable synchronized scrolling."""
        self.sync_scroll_enabled = enabled

    def scroll_to_percentage(self, percentage: float):
        """Scroll webview with smooth 60fps animation."""
        if not self.sync_scroll_enabled or self._is_programmatic_scroll:
            return

        self._is_programmatic_scroll = True
        self._target_scroll_percentage = max(0.0, min(1.0, percentage))

        # Smooth scroll with requestAnimationFrame
        js_code = f"""
        (function() {{
            const targetPercentage = {self._target_scroll_percentage};
            const maxScroll = Math.max(
                document.documentElement.scrollHeight - window.innerHeight,
                0
            );
            const targetScroll = maxScroll * targetPercentage;
            const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
            const distance = targetScroll - currentScroll;
            
            // Cancel any existing animation
            if (window.scrollAnimation) {{
                cancelAnimationFrame(window.scrollAnimation);
            }}
            
            // For small movements, jump instantly
            if (Math.abs(distance) < 5) {{
                window.scrollTo(0, targetScroll);
                return;
            }}
            
            // Smooth animation at 60fps
            const startTime = performance.now();
            const duration = 100; // 100ms for quick response
            
            function animate(currentTime) {{
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Ease-out quad for smooth feel
                const eased = 1 - (1 - progress) * (1 - progress);
                const current = currentScroll + (distance * eased);
                
                window.scrollTo(0, current);
                
                if (progress < 1) {{
                    window.scrollAnimation = requestAnimationFrame(animate);
                }} else {{
                    window.scrollAnimation = null;
                }}
            }}
            
            window.scrollAnimation = requestAnimationFrame(animate);
        }})();
        """

        try:
            self.webview.evaluate_javascript(js_code, -1, None, None, None)
        except Exception as e:
            print(f"Error scrolling webview: {e}")

        # Reset flag after animation
        GLib.timeout_add(
            150, lambda: setattr(self, "_is_programmatic_scroll", False) or False
        )

    def get_scroll_percentage(self, callback: Callable[[float], None]):
        """Get current scroll percentage."""
        if not self.sync_scroll_enabled:
            callback(0.0)
            return

        js_code = """
        (function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
            if (scrollHeight <= 0) {
                document.title = 'scroll:0.0';
                return 0.0;
            }
            const percentage = scrollTop / scrollHeight;
            document.title = 'scroll:' + percentage.toFixed(6);
            return percentage;
        })();
        """

        try:
            self.webview.evaluate_javascript(js_code, -1, None, None, None)
            GLib.timeout_add(16, lambda: self._read_scroll_from_title(callback))
        except Exception as e:
            GLib.idle_add(lambda: callback(0.0))

    def _read_scroll_from_title(self, callback: Callable[[float], None]):
        """Read scroll percentage from document title."""
        try:
            title = self.webview.get_title()
            if title and title.startswith("scroll:"):
                percentage = float(title.split(":")[1])
                callback(percentage)
            else:
                callback(0.0)
        except Exception:
            callback(0.0)
        return False

    def connect_scroll_changed(self, callback: Callable[[float], None]):
        """Register a callback for webview scroll changes."""
        self._scroll_callbacks.append(callback)

    def setup_scroll_monitoring(self):
        """Setup optimized scroll monitoring."""
        if self._scroll_sync_handler_id:
            return

        js_code = """
        (function() {
            if (window.scrollMonitorInitialized) return;
            window.scrollMonitorInitialized = true;
            
            window.lastScrollPercentage = 0;
            let lastUpdate = 0;
            const throttleMs = 16; // 60fps throttle
            
            function checkScroll() {
                const now = Date.now();
                if (now - lastUpdate < throttleMs) {
                    return;
                }
                lastUpdate = now;
                
                const currentScrollY = window.pageYOffset || document.documentElement.scrollTop;
                const maxScroll = Math.max(
                    document.documentElement.scrollHeight - window.innerHeight,
                    0
                );
                const percentage = maxScroll === 0 ? 0 : currentScrollY / maxScroll;
                
                // Update on meaningful change
                if (Math.abs(percentage - window.lastScrollPercentage) > 0.003) {
                    window.lastScrollPercentage = percentage;
                    document.title = 'scroll:' + percentage.toFixed(6);
                }
            }
            
            // Use scroll event with throttling
            window.addEventListener('scroll', checkScroll, { passive: true });
            
            // Also poll at 60fps for continuous tracking
            setInterval(checkScroll, 16);
        })();
        """

        try:
            self.webview.evaluate_javascript(js_code, -1, None, None, None)
            self._scroll_sync_handler_id = True
            self._start_scroll_polling()
        except Exception as e:
            print(f"Error setting up scroll monitoring: {e}")

    def _start_scroll_polling(self):
        """Start optimized polling at 60fps."""

        def poll_scroll():
            if not self.sync_scroll_enabled or self._is_programmatic_scroll:
                return True

            def on_scroll_result(percentage):
                if (
                    not self._is_programmatic_scroll
                    and abs(percentage - self._current_scroll_percentage) > 0.003
                ):
                    self._current_scroll_percentage = percentage
                    for callback in self._scroll_callbacks:
                        try:
                            callback(percentage)
                        except Exception:
                            pass

            self.get_scroll_percentage(on_scroll_result)
            return True

        # Poll at 60fps (16ms)
        GLib.timeout_add(16, poll_scroll)

    def _on_theme_changed(self, style_manager, param):
        """Fast theme switching."""
        is_dark = style_manager.get_dark()
        if is_dark != self._last_is_dark:
            self._last_is_dark = is_dark
            if self._last_html:
                # Reload with the same HTML to update colors
                self.load_html(self._last_html, is_dark=is_dark)


    def _apply_theme_instantly(self, is_dark):
        """Apply theme instantly using CSS injection."""
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#d4d4d4" if is_dark else "#1e1e1e"
        link_color = "#4fc3f7" if is_dark else "#0066cc"
        code_bg = "#2d2d2d" if is_dark else "#f5f5f5"
        pre_bg = "#2d2d2d" if is_dark else "#f5f5f5"
        border_color = "#333333" if is_dark else "#e1e4e8"
        mermaid_theme = "dark" if is_dark else "default"

        if is_dark:
            note_bg, note_border = "#1f6feb1a", "#2f81f7"
            tip_bg, tip_border = "#3fb9501a", "#3fb950"
            important_bg, important_border = "#a371f71a", "#a371f7"
            warning_bg, warning_border = "#d299221a", "#d29922"
            caution_bg, caution_border = "#f851301a", "#f85149"
        else:
            note_bg, note_border = "#ddf4ff", "#0969da"
            tip_bg, tip_border = "#dafbe1", "#1a7f37"
            important_bg, important_border = "#f8e3ff", "#8250df"
            warning_bg, warning_border = "#fff8c5", "#9a6700"
            caution_bg, caution_border = "#ffebe9", "#cf222e"

        js_code = f"""
        (function() {{
            let style = document.getElementById('dynamic-theme');
            if (!style) {{
                style = document.createElement('style');
                style.id = 'dynamic-theme';
                document.head.appendChild(style);
            }}
            style.innerHTML = `
                body {{ background: {bg_color}; color: {text_color}; }}
                a {{ color: {link_color}; }}
                code {{ background: {code_bg}; }}
                pre {{ background: {pre_bg}; border-color: {border_color}; }}
                .alert-note {{ background: {note_bg}; border-color: {note_border}; }}
                .alert-tip {{ background: {tip_bg}; border-color: {tip_border}; }}
                .alert-important {{ background: {important_bg}; border-color: {important_border}; }}
                .alert-warning {{ background: {warning_bg}; border-color: {warning_border}; }}
                .alert-caution {{ background: {caution_bg}; border-color: {caution_border}; }}
            `;
            
            if (window.mermaid) {{
                window.mermaid.initialize({{ theme: '{mermaid_theme}' }});
                document.querySelectorAll('.mermaid').forEach(el => {{
                    if (!el.getAttribute('data-processed')) {{
                        window.mermaid.run({{ nodes: [el] }});
                    }}
                }});
            }}
        }})();
        """

        try:
            self.webview.evaluate_javascript(js_code, -1, None, None, None)
        except Exception as e:
            print(f"Error applying theme: {e}")

    def _on_decide_policy(self, webview, decision, decision_type):
        """Handle navigation decisions."""
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
        """Handle context menu."""
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

        return False

    def is_dark_mode(self) -> bool:
        """Check if the current theme is dark."""
        style_manager = Adw.StyleManager.get_default()
        return style_manager.get_dark()

    def _process_github_alerts(self, html: str) -> str:
        """Convert GitHub-style alerts to styled divs."""
        svg_icons = {
            "NOTE": """<svg viewBox="0 0 16 16" width="16" height="16"><path d="M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v9.5A1.75 1.75 0 0 1 14.25 13H8.06l-2.573 2.573A1.458 1.458 0 0 1 3 14.543V13H1.75A1.75 1.75 0 0 1 0 11.25Zm1.75-.25a.25.25 0 0 0-.25.25v9.5c0 .138.112.25.25.25h2a.75.75 0 0 1 .75.75v2.19l2.72-2.72a.749.749 0 0 1 .53-.22h6.5a.25.25 0 0 0 .25-.25v-9.5a.25.25 0 0 0-.25-.25Zm7 2.25v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0ZM9 9a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"></path></svg>""",
            "TIP": """<svg viewBox="0 0 16 16" width="16" height="16"><path d="M8 1.5c-2.363 0-4 1.69-4 3.75 0 .984.424 1.625.984 2.304l.214.253c.223.264.47.556.673.848.284.411.537.896.621 1.49a.75.75 0 0 1-1.484.211c-.04-.282-.163-.547-.37-.847a8.456 8.456 0 0 0-.542-.68c-.084-.1-.173-.205-.268-.32C3.201 7.75 2.5 6.766 2.5 5.25 2.5 2.31 4.863 0 8 0s5.5 2.31 5.5 5.25c0 1.516-.701 2.5-1.328 3.259-.095.115-.184.22-.268.319-.207.245-.383.453-.541.681-.208.3-.33.565-.37.847a.751.751 0 0 1-1.485-.212c.084-.593.337-1.078.621-1.489.203-.292.45-.584.673-.848.075-.088.147-.173.213-.253.561-.679.985-1.32.985-2.304 0-2.06-1.637-3.75-4-3.75ZM5.75 12h4.5a.75.75 0 0 1 0 1.5h-4.5a.75.75 0 0 1 0-1.5ZM6 15.25a.75.75 0 0 1 .75-.75h2.5a.75.75 0 0 1 0 1.5h-2.5a.75.75 0 0 1-.75-.75Z"></path></svg>""",
            "IMPORTANT": """<svg viewBox="0 0 16 16" width="16" height="16"><path d="M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v9.5A1.75 1.75 0 0 1 14.25 13H8.06l-2.573 2.573A1.458 1.458 0 0 1 3 14.543V13H1.75A1.75 1.75 0 0 1 0 11.25Zm1.75-.25a.25.25 0 0 0-.25.25v9.5c0 .138.112.25.25.25h2a.75.75 0 0 1 .75.75v2.19l2.72-2.72a.749.749 0 0 1 .53-.22h6.5a.25.25 0 0 0 .25-.25v-9.5a.25.25 0 0 0-.25-.25Zm7 2.25v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0ZM9 9a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"></path></svg>""",
            "WARNING": """<svg viewBox="0 0 16 16" width="16" height="16"><path d="M6.457 1.047c.659-1.234 2.427-1.234 3.086 0l6.082 11.378A1.75 1.75 0 0 1 14.082 15H1.918a1.75 1.75 0 0 1-1.543-2.575Zm1.763.707a.25.25 0 0 0-.44 0L1.698 13.132a.25.25 0 0 0 .22.368h12.164a.25.25 0 0 0 .22-.368Zm.53 3.996v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0ZM9 11a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"></path></svg>""",
            "CAUTION": """<svg viewBox="0 0 16 16" width="16" height="16"><path d="M4.47.22A.749.749 0 0 1 5 0h6c.199 0 .389.079.53.22l4.25 4.25c.141.14.22.331.22.53v6a.749.749 0 0 1-.22.53l-4.25 4.25A.749.749 0 0 1 11 16H5a.749.749 0 0 1-.53-.22L.22 11.53A.749.749 0 0 1 0 11V5c0-.199.079-.389.22-.53Zm.84 1.28L1.5 5.31v5.38l3.81 3.81h5.38l3.81-3.81V5.31L10.69 1.5ZM8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"></path></svg>""",
        }

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

            icon_svg = svg_icons.get(alert_type, svg_icons["NOTE"])
            return f"""<div class="alert alert-{alert_type.lower()}">
        <div class="alert-title">
            {icon_svg}
            <span class="alert-title-text">{alert_type.title()}</span>
        </div>
        <div class="alert-content">{full_content}</div>
    </div>"""

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
        """Manually set the theme and update the webview immediately."""
        self._last_is_dark = is_dark
        if self._last_html:
            # Reload the last HTML with new theme
            self.load_html(self._last_html, is_dark=is_dark)


    def _load_external_file(self, filename: str) -> str:
        """Load content from external file."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return ""

    def load_html(self, html: str, is_dark: Optional[bool] = None):
        """Load HTML content with GPU-accelerated rendering."""
        if is_dark is None:
            is_dark = self.is_dark_mode()

        self._last_html = html
        self._last_is_dark = is_dark

        def process_html_async():
            with self._rendering_lock:
                try:
                    cache_key = (hash(html), is_dark)
                    if cache_key in self._html_cache:
                        html_content = self._html_cache[cache_key]
                        GLib.idle_add(lambda: self._finish_load_html(html_content))
                        return

                    processed_html = self._process_mermaid_blocks(html)
                    processed_html = self._process_github_alerts(processed_html)

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

                    bg_color = "#1e1e1e" if is_dark else "#ffffff"
                    text_color = "#d4d4d4" if is_dark else "#1e1e1e"
                    link_color = "#4fc3f7" if is_dark else "#0066cc"
                    code_bg = "#2d2d2d" if is_dark else "#f5f5f5"
                    pre_bg = "#2d2d2d" if is_dark else "#f5f5f5"
                    border_color = "#333333" if is_dark else "#e1e4e8"
                    mermaid_theme = "dark" if is_dark else "default"

                    if is_dark:
                        note_bg, note_border, note_icon = (
                            "#1f6feb1a",
                            "#2f81f7",
                            "#2f81f7",
                        )
                        tip_bg, tip_border, tip_icon = "#3fb9501a", "#3fb950", "#3fb950"
                        important_bg, important_border, important_icon = (
                            "#a371f71a",
                            "#a371f7",
                            "#a371f7",
                        )
                        warning_bg, warning_border, warning_icon = (
                            "#d299221a",
                            "#d29922",
                            "#d29922",
                        )
                        caution_bg, caution_border, caution_icon = (
                            "#f851301a",
                            "#f85149",
                            "#f85149",
                        )
                    else:
                        note_bg, note_border, note_icon = (
                            "#ddf4ff",
                            "#0969da",
                            "#0969da",
                        )
                        tip_bg, tip_border, tip_icon = "#dafbe1", "#1a7f37", "#1a7f37"
                        important_bg, important_border, important_icon = (
                            "#f8e3ff",
                            "#8250df",
                            "#8250df",
                        )
                        warning_bg, warning_border, warning_icon = (
                            "#fff8c5",
                            "#9a6700",
                            "#9a6700",
                        )
                        caution_bg, caution_border, caution_icon = (
                            "#ffebe9",
                            "#cf222e",
                            "#cf222e",
                        )

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

<!-- Mermaid for diagrams -->
<script type="module">
{js_mermaid_with_theme}
</script>

<!-- MathJax for LaTeX -->
<script>
{js_mathjax_config}
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>

<script>
{js_mathjax_render}
</script>
</head>
<body>
{processed_html}
</body>
</html>"""

                    self._html_cache[cache_key] = html_content
                    if len(self._html_cache) > 10:
                        self._html_cache.clear()

                    GLib.idle_add(lambda: self._finish_load_html(html_content))

                except Exception as e:
                    print(f"Error rendering markdown: {e}")

        self._thread_pool.submit(process_html_async)

    def _finish_load_html(self, html_content):
        """Finish loading HTML in main thread."""
        self.webview.load_html(html_content, "file:///")
        GLib.timeout_add(100, self.setup_scroll_monitoring)

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
