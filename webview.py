import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, WebKit, Adw
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

        # Process GitHub-style alerts
        html = self._process_github_alerts(html)

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

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style id="theme-style">
* {{
    box-sizing: border-box;
}}
body {{ 
    background: {bg_color}; 
    color: {text_color}; 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
    padding: 20px; 
    line-height: 1.6;
    max-width: 900px;
    margin: 0 auto;
}}
a {{ 
    color: {link_color}; 
    text-decoration: none;
}}
a:hover {{
    text-decoration: underline;
}}
code {{ 
    background: {code_bg}; 
    padding: 2px 6px; 
    border-radius: 3px; 
    font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
    font-size: 0.9em;
}}
pre {{ 
    background: {pre_bg}; 
    padding: 16px; 
    border-radius: 6px; 
    overflow-x: auto;
    border: 1px solid {border_color};
}}
pre code {{ 
    background: none; 
    padding: 0; 
}}
blockquote {{
    border-left: 4px solid {border_color};
    padding-left: 16px;
    margin-left: 0;
    color: {text_color};
    opacity: 0.8;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
}}
th, td {{
    border: 1px solid {border_color};
    padding: 8px 12px;
    text-align: left;
}}
th {{
    background: {code_bg};
    font-weight: 600;
}}
.mermaid {{
    text-align: center;
    margin: 20px 0;
    background: transparent;
}}

/* GitHub-style alerts */
.alert {{
    padding: 12px 16px;
    margin: 16px 0;
    border-left: 4px solid;
    border-radius: 6px;
    position: relative;
}}
.alert::before {{
    content: '';
    font-weight: 600;
    margin-right: 8px;
    font-size: 16px;
}}
.alert-note {{
    background: {note_bg};
    border-color: {note_border};
}}
.alert-note::before {{
    content: '📘 NOTE';
    color: {note_icon};
}}
.alert-tip {{
    background: {tip_bg};
    border-color: {tip_border};
}}
.alert-tip::before {{
    content: '💡 TIP';
    color: {tip_icon};
}}
.alert-important {{
    background: {important_bg};
    border-color: {important_border};
}}
.alert-important::before {{
    content: '❗ IMPORTANT';
    color: {important_icon};
}}
.alert-warning {{
    background: {warning_bg};
    border-color: {warning_border};
}}
.alert-warning::before {{
    content: '⚠️ WARNING';
    color: {warning_icon};
}}
.alert-caution {{
    background: {caution_bg};
    border-color: {caution_border};
}}
.alert-caution::before {{
    content: '🚫 CAUTION';
    color: {caution_icon};
}}
.alert p:first-child {{
    margin-top: 0;
}}
.alert p:last-child {{
    margin-bottom: 0;
}}

h1, h2, h3, h4, h5, h6 {{
    margin-top: 24px;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.25;
}}
h1 {{
    font-size: 2em;
    border-bottom: 1px solid {border_color};
    padding-bottom: 8px;
}}
h2 {{
    font-size: 1.5em;
    border-bottom: 1px solid {border_color};
    padding-bottom: 8px;
}}
ul, ol {{
    padding-left: 2em;
}}
li {{
    margin: 4px 0;
}}
hr {{
    border: none;
    border-top: 2px solid {border_color};
    margin: 24px 0;
}}
img {{
    max-width: 100%;
    height: auto;
}}

/* MathJax styling */
.MathJax {{
    outline: 0;
}}
mjx-container {{
    display: inline-block;
    margin: 0 2px;
}}
mjx-container[display="true"] {{
    display: block;
    text-align: center;
    margin: 1em 0;
}}
</style>

<!-- MathJax for LaTeX (Full Support) -->
<script>
window.MathJax = {{
    tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        processEscapes: true,
        processEnvironments: true,
        packages: {{'[+]': ['ams', 'newcommand', 'configmacros', 'action', 'unicode']}},
        tags: 'ams',
        macros: {{
            RR: '{{\\\\mathbb{{R}}}}',
            NN: '{{\\\\mathbb{{N}}}}',
            ZZ: '{{\\\\mathbb{{Z}}}}',
            QQ: '{{\\\\mathbb{{Q}}}}',
            CC: '{{\\\\mathbb{{C}}}}'
        }}
    }},
    svg: {{
        fontCache: 'global'
    }},
    options: {{
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
        ignoreHtmlClass: 'no-mathjax'
    }},
    startup: {{
        pageReady: () => {{
            return MathJax.startup.defaultPageReady();
        }}
    }}
}};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<!-- Mermaid for diagrams (Latest Version v11) -->
<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';

mermaid.initialize({{ 
    startOnLoad: true,
    theme: '{mermaid_theme}',
    securityLevel: 'loose',
    flowchart: {{
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
    }},
    sequence: {{
        useMaxWidth: true,
        wrap: true
    }},
    gantt: {{
        useMaxWidth: true
    }},
    er: {{
        useMaxWidth: true
    }},
    pie: {{
        useMaxWidth: true
    }},
    quadrantChart: {{
        useMaxWidth: true
    }},
    xyChart: {{
        useMaxWidth: true
    }},
    timeline: {{
        useMaxWidth: true
    }},
    mindmap: {{
        useMaxWidth: true
    }},
    gitGraph: {{
        useMaxWidth: true
    }},
    c4: {{
        useMaxWidth: true
    }},
    sankey: {{
        useMaxWidth: true
    }},
    block: {{
        useMaxWidth: true
    }}
}});

// Ensure MathJax renders after page load
window.addEventListener('load', () => {{
    if (window.MathJax) {{
        MathJax.typesetPromise().catch((err) => console.log('MathJax error:', err));
    }}
}});
</script>
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
