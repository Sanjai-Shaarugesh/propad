import gi
import os
import tempfile
import re
import threading
from concurrent.futures import ThreadPoolExecutor

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Adw, Gio, WebKit, GLib, Gdk
import comrak
from propad.i18n import _


UI_FILE = "ui/export_dialog.ui"


@Gtk.Template(filename=UI_FILE)
class ExportDialog(Adw.Window):
    __gtype_name__ = "ExportDialog"

    btn_export_html = Gtk.Template.Child()
    btn_export_pdf = Gtk.Template.Child()
    btn_export_image = Gtk.Template.Child()
    btn_close = Gtk.Template.Child()
    check_include_css = Gtk.Template.Child()
    check_standalone = Gtk.Template.Child()
    dropdown_image_format = Gtk.Template.Child()

    def __init__(self, parent_window, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(parent_window)
        self.parent_window = parent_window

        # Thread pool for parallel processing
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

        # Cache for loaded external files
        self._file_cache = {}

        self._preload_external_files()

        self._setup_webkit_context()

        self.extension_options = comrak.ExtensionOptions()
        self.extension_options.table = True
        self.extension_options.strikethrough = True
        self.extension_options.autolink = True
        self.extension_options.tasklist = True
        self.extension_options.superscript = True
        self.extension_options.footnotes = True

        # Connect signals
        self.btn_export_html.connect("clicked", self._on_export_html)
        self.btn_export_pdf.connect("clicked", self._on_export_pdf)
        self.btn_export_image.connect("clicked", self._on_export_image)
        self.btn_close.connect("clicked", lambda b: self.close())

    def _setup_webkit_context(self):
        try:
            os.environ["WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS"] = "1"
            os.environ["WEBKIT_FORCE_SANDBOX"] = "0"

            context = WebKit.WebContext.get_default()

            if hasattr(context, "set_process_model"):
                try:
                    context.set_process_model(
                        WebKit.ProcessModel.SHARED_SECONDARY_PROCESS
                    )
                except:
                    pass

            try:
                context.set_cache_model(WebKit.CacheModel.DOCUMENT_VIEWER)
            except:
                pass

            print("WebKit sandbox disabled for Flatpak compatibility")
        except Exception as e:
            print(f"Note: WebKit context configuration skipped: {e}")
            # Continue anyway - the environment variables should work

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

    def get_markdown_content(self):
        if self.parent_window:
            sidebar = self.parent_window.get_sidebar()
            return sidebar.get_text()
        return ""

    def _load_external_file(self, filename):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return ""

    def get_html_content(self):
        markdown = self.get_markdown_content()
        html = comrak.render_markdown(
            markdown, extension_options=self.extension_options
        )
        return html

    def get_full_html_document_from_webview(self, for_pdf=False):
        if not self.parent_window:
            return ""

        markdown = self.get_markdown_content()
        html = comrak.render_markdown(
            markdown, extension_options=self.extension_options
        )

        def process_mermaid_blocks(html_content):
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

            result = html_content
            for pattern in patterns:
                result = pattern.sub(replace_mermaid, result)
            return result

        # Process GitHub alerts (same as webview.py)
        def process_github_alerts(html_content):
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

            return alert_pattern.sub(replace_alert, html_content)

        processed_html = process_mermaid_blocks(html)
        processed_html = process_github_alerts(processed_html)

        is_dark = (
            False
            if for_pdf
            else (self.parent_window.is_dark_mode() if self.parent_window else False)
        )

        def load_external_file(filename):
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(script_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                return ""

        # Use cached files if available, otherwise load
        css_content = self._file_cache.get("assets/styles.css") or load_external_file(
            "assets/styles.css"
        )
        js_mermaid = self._file_cache.get(
            "assets/mermaid-loader.js"
        ) or load_external_file("assets/mermaid-loader.js")
        js_mathjax_config = self._file_cache.get(
            "assets/mathjax-config.js"
        ) or load_external_file("assets/mathjax-config.js")
        js_mathjax_render = self._file_cache.get(
            "assets/mathjax-render.js"
        ) or load_external_file("assets/mathjax-render.js")

        # Theme colors
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
            warning_bg, warning_border, warning_icon = "#3a2e1e", "#f59e0b", "#f59e0b"
            caution_bg, caution_border, caution_icon = "#3a1e1e", "#ef4444", "#ef4444"
        else:
            note_bg, note_border, note_icon = "#dbeafe", "#3b82f6", "#1e40af"
            tip_bg, tip_border, tip_icon = "#d1fae5", "#10b981", "#065f46"
            important_bg, important_border, important_icon = (
                "#f3e8ff",
                "#a855f7",
                "#6b21a8",
            )
            warning_bg, warning_border, warning_icon = "#fef3c7", "#f59e0b", "#92400e"
            caution_bg, caution_border, caution_icon = "#fee2e2", "#ef4444", "#991b1b"

        # Replace CSS variables
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

        # Replace JS variables
        js_mermaid_with_theme = js_mermaid.replace("{mermaid_theme}", mermaid_theme)

        # Build complete HTML document
        html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Exported Document</title>
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
<script propad="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<!-- Ensure MathJax renders after page load -->
<script>
{js_mathjax_render}
</script>
</head>
<body>
{processed_html}
</body>
</html>"""

        return html_doc

    def _on_export_html(self, button):
        """Export as HTML - Fixed version."""
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Export as HTML"))

        if (
            self.parent_window
            and hasattr(self.parent_window, "current_file")
            and self.parent_window.current_file
        ):
            base_name = os.path.splitext(
                os.path.basename(self.parent_window.current_file)
            )[0]
            dialog.set_initial_name(f"{base_name}.html")

            current_dir = os.path.dirname(self.parent_window.current_file)
            if current_dir and os.path.exists(current_dir):
                dialog.set_initial_folder(Gio.File.new_for_path(current_dir))
        else:
            dialog.set_initial_name("document.html")
            # Set to user's Documents or Home directory
            home_dir = os.path.expanduser("~")
            docs_dir = os.path.join(home_dir, "Documents")
            if os.path.exists(docs_dir):
                dialog.set_initial_folder(Gio.File.new_for_path(docs_dir))
            else:
                dialog.set_initial_folder(Gio.File.new_for_path(home_dir))

        filter_html = Gtk.FileFilter()
        filter_html.set_name(_("HTML Files"))
        filter_html.add_pattern("*.html")
        filter_html.add_pattern("*.htm")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_html)
        dialog.set_filters(filters)

        dialog.save(self, None, self._on_export_html_response, None)

    def _on_export_html_response(self, dialog, result, user_data):
        """Handle HTML export response - Fixed version with direct file writing."""
        try:
            file = dialog.save_finish(result)
            if file:
                html_content = self.get_full_html_document_from_webview(for_pdf=False)

                filepath = file.get_path()

                if filepath and "/run/user/" in filepath and "/doc/" in filepath:
                    self._show_error_message(
                        "Permission Error",
                        "The app needs filesystem access. Please rebuild with --filesystem=host",
                    )
                    return

                if filepath:
                    try:
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)

                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(html_content)

                        self._show_success_message(
                            "HTML Export Successful",
                            f"Document exported to:\n{filepath}",
                        )
                    except Exception as write_error:
                        try:
                            output_stream = file.replace(
                                None,
                                False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION,
                                None,
                            )
                            output_stream.write(html_content.encode("utf-8"), None)
                            output_stream.close(None)

                            self._show_success_message(
                                "HTML Export Successful",
                                f"Document exported successfully!",
                            )
                        except Exception as gio_error:
                            self._show_error_message(
                                "Export Failed",
                                f"Could not write file: {str(write_error)}",
                            )
                else:
                    self._show_error_message(
                        "Export Failed", "Could not determine file path"
                    )

        except GLib.Error as e:
            # Handle dialog cancellation gracefully
            if e.code != Gtk.DialogError.DISMISSED:
                self._show_error_message(
                    "Export Failed", f"Could not export to HTML: {e.message}"
                )
        except Exception as e:
            self._show_error_message(
                "Export Failed", f"Could not export to HTML: {str(e)}"
            )

    def _on_export_pdf(self, button):
        """Export as PDF using WebKit print operation with GTK print dialog."""
        html_content = self.get_full_html_document_from_webview(for_pdf=True)

        if (
            self.parent_window
            and hasattr(self.parent_window, "current_file")
            and self.parent_window.current_file
        ):
            base_name = os.path.splitext(
                os.path.basename(self.parent_window.current_file)
            )[0]
            export_filename = f"{base_name}.pdf"
        else:
            export_filename = "document.pdf"

        home_dir = os.path.expanduser("~")
        default_output = os.path.join(home_dir, export_filename)

        self._pdf_html_content = html_content
        self._pdf_output_path = default_output

        # Load HTML and show print dialog
        self._prepare_pdf_webview()

    def _prepare_pdf_webview(self):
        settings = WebKit.Settings()
        settings.set_enable_webgl(True)
        settings.set_enable_webaudio(True)
        settings.set_hardware_acceleration_policy(
            WebKit.HardwareAccelerationPolicy.ALWAYS
        )
        settings.set_enable_page_cache(True)
        settings.set_enable_javascript(True)

        webview = WebKit.WebView()
        webview.set_settings(settings)
        webview.set_size_request(800, 600)

        try:
            webview.set_background_color(Gdk.RGBA(1, 1, 1, 1))
        except:
            pass

        self._pdf_webview = webview
        self._render_timeout_id = None

        def on_load_finished(web_view, event):
            if event == WebKit.LoadEvent.FINISHED:
                GLib.idle_add(self._show_print_dialog_immediate)

        webview.connect("load-changed", on_load_finished)

        self._pdf_html_content = self.get_full_html_document_from_webview(for_pdf=True)

        def load_html_async():
            GLib.idle_add(lambda: webview.load_html(self._pdf_html_content, "file:///"))

        self._thread_pool.submit(load_html_async)

    def _show_print_dialog_immediate(self):
        self._render_timeout_id = GLib.timeout_add(200, self._show_print_dialog)
        return False

    def _show_print_dialog(self):
        try:
            self._render_timeout_id = None

            print_op = WebKit.PrintOperation.new(self._pdf_webview)

            page_setup = Gtk.PageSetup()
            paper_size = Gtk.PaperSize.new(Gtk.PAPER_NAME_A4)
            page_setup.set_paper_size(paper_size)
            page_setup.set_top_margin(15, Gtk.Unit.MM)
            page_setup.set_bottom_margin(15, Gtk.Unit.MM)
            page_setup.set_left_margin(15, Gtk.Unit.MM)
            page_setup.set_right_margin(15, Gtk.Unit.MM)

            print_settings = Gtk.PrintSettings()
            print_settings.set(
                Gtk.PRINT_SETTINGS_OUTPUT_URI, f"file://{self._pdf_output_path}"
            )
            print_settings.set(Gtk.PRINT_SETTINGS_OUTPUT_FILE_FORMAT, "pdf")

            print_settings.set_use_color(True)
            print_settings.set_quality(Gtk.PrintQuality.HIGH)
            print_settings.set_resolution(300)  # 300 DPI for better quality

            print_settings.set_printer("Print to File")

            print_op.set_page_setup(page_setup)
            print_op.set_print_settings(print_settings)

            print_op.connect("finished", self._on_print_finished)
            print_op.connect("failed", self._on_print_failed)

            response = print_op.run_dialog(self)

            return False

        except Exception as e:
            self._show_error_message(
                "Export Failed", f"Could not show print dialog: {str(e)}"
            )
            return False

    def _on_print_finished(self, print_op):
        settings = print_op.get_print_settings()
        output_uri = settings.get(Gtk.PRINT_SETTINGS_OUTPUT_URI)

        if output_uri and output_uri.startswith("file://"):
            filepath = output_uri[7:]

            self._show_success_message(
                "PDF Export Successful", f"Document exported to:\n{filepath}"
            )
        else:
            self._show_success_message(
                "Print Successful", "Document was printed successfully"
            )

    def _on_print_failed(self, print_op, error):
        error_msg = error.message if error else "Unknown error"

        self._show_error_message(
            "Export Failed", f"Could not generate PDF: {error_msg}"
        )

    def _on_export_image(self, button):
        formats = ["png", "jpg", "webp"]
        selected_index = self.dropdown_image_format.get_selected()
        format_ext = formats[selected_index]

        dialog = Gtk.FileDialog()
        dialog.set_title(_("Export as Image"))

        if (
            self.parent_window
            and hasattr(self.parent_window, "current_file")
            and self.parent_window.current_file
        ):
            base_name = os.path.splitext(
                os.path.basename(self.parent_window.current_file)
            )[0]
            dialog.set_initial_name(f"{base_name}.{format_ext}")

            current_dir = os.path.dirname(self.parent_window.current_file)
            if current_dir and os.path.exists(current_dir):
                dialog.set_initial_folder(Gio.File.new_for_path(current_dir))
        else:
            dialog.set_initial_name(f"document.{format_ext}")

            home_dir = os.path.expanduser("~")
            docs_dir = os.path.join(home_dir, "Documents")
            if os.path.exists(docs_dir):
                dialog.set_initial_folder(Gio.File.new_for_path(docs_dir))
            else:
                dialog.set_initial_folder(Gio.File.new_for_path(home_dir))

        filter_img = Gtk.FileFilter()
        filter_img.set_name(f"{_(format_ext.upper())} Files")
        filter_img.add_pattern(f"*.{format_ext}")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_img)
        dialog.set_filters(filters)

        dialog.save(self, None, self._on_export_image_response, format_ext)

    def _on_export_image_response(self, dialog, result, format_ext):
        """Handle image export response - Fixed version with proper path handling."""
        try:
            file = dialog.save_finish(result)
            if file:
                self._generate_image(file, format_ext)
        except GLib.Error as e:
            if e.code != Gtk.DialogError.DISMISSED:
                self._show_error_message(
                    "Export Failed", f"Could not export to image: {e.message}"
                )
        except Exception as e:
            self._show_error_message(
                "Export Failed", f"Could not export to image: {str(e)}"
            )

    def _generate_image(self, filepath, format_ext, width=1920, height=1080):
        """Generate image from HTML content."""
        settings = WebKit.Settings()
        settings.set_enable_webgl(True)
        settings.set_hardware_acceleration_policy(
            WebKit.HardwareAccelerationPolicy.ALWAYS
        )
        settings.set_enable_javascript(True)

        STANDARD_WIDTH = 1920
        STANDARD_HEIGHT = 1080

        webview = WebKit.WebView()
        webview.set_settings(settings)

        webview.set_size_request(STANDARD_WIDTH, STANDARD_HEIGHT)

        html_content = self.get_full_html_document_from_webview(for_pdf=False)

        def on_snapshot_ready(source, result, user_data):
            try:
                texture = webview.get_snapshot_finish(result)

                path_str = (
                    filepath.get_path() if isinstance(filepath, Gio.File) else filepath
                )

                success = texture.save_to_png(path_str)

                if success and os.path.exists(filepath):
                    self._show_success_message(
                        f"{format_ext.upper()} Export Successful",
                        f"Document exported to:\n{os.path.basename(filepath)}",
                    )
                else:
                    raise Exception("Failed to save image")
            except Exception as e:
                import traceback

                self._show_error_message(
                    "Export Failed", f"Could not save image: {str(e)}"
                )

        def on_load_finished(web_view, event):
            if event == WebKit.LoadEvent.FINISHED:
                GLib.timeout_add(500, lambda: take_snapshot())

        def take_snapshot():
            webview.get_snapshot(
                WebKit.SnapshotRegion.FULL_DOCUMENT,
                WebKit.SnapshotOptions.NONE,
                None,
                on_snapshot_ready,
                None,
            )

        webview.connect("load-changed", on_load_finished)
        webview.load_html(html_content, "file:///")

    def _show_success_message(self, heading, body):
        """Show success message dialog."""
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading(heading)
        dialog.set_body(body)
        dialog.add_response("ok", "OK")
        dialog.present()

    def _show_error_message(self, heading, body):
        """Show error message dialog."""
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading(heading)
        dialog.set_body(body)
        dialog.add_response("ok", "OK")
        dialog.present()
