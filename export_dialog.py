import gi
import os
import base64

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, Adw, Gio, WebKit
import comrak

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

        # Connect signals
        self.btn_export_html.connect("clicked", self._on_export_html)
        self.btn_export_pdf.connect("clicked", self._on_export_pdf)
        self.btn_export_image.connect("clicked", self._on_export_image)
        self.btn_close.connect("clicked", lambda b: self.close())

    def get_markdown_content(self):
        """Get markdown content from parent window."""
        if self.parent_window:
            sidebar = self.parent_window.get_sidebar()
            return sidebar.get_text()
        return ""

    def get_html_content(self):
        """Convert markdown to HTML."""
        markdown = self.get_markdown_content()
        html = comrak.render_markdown(
            markdown, extension_options=comrak.ExtensionOptions()
        )
        return html

    def get_full_html_document(self):
        """Get complete HTML document with styling."""
        html_body = self.get_html_content()
        is_dark = self.parent_window.is_dark_mode() if self.parent_window else False

        # Load CSS if needed
        css_content = ""
        if self.check_include_css.get_active():
            try:
                css_file = os.path.join(
                    os.path.dirname(__file__), "assets", "styles.css"
                )
                with open(css_file, "r") as f:
                    css_content = f.read()
            except Exception as e:
                print(f"Error loading CSS: {e}")

        # Theme colors
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#d4d4d4" if is_dark else "#1e1e1e"

        html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exported Document</title>
    <style>
        body {{
            background: {bg_color};
            color: {text_color};
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        {css_content}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: '{"dark" if is_dark else "default"}' }});
    </script>
</head>
<body>
{html_body}
</body>
</html>"""
        return html_doc

    def _on_export_html(self, button):
        """Export as HTML."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Export as HTML")
        dialog.set_initial_name("document.html")

        filter_html = Gtk.FileFilter()
        filter_html.set_name("HTML Files")
        filter_html.add_pattern("*.html")
        filter_html.add_pattern("*.htm")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_html)
        dialog.set_filters(filters)

        dialog.save(self, None, self._on_export_html_response)

    def _on_export_html_response(self, dialog, result):
        """Handle HTML export response."""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()
                html_content = self.get_full_html_document()

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)

                print(f"Exported to HTML: {filepath}")
                self._show_success_toast("Exported to HTML successfully!")
        except Exception as e:
            print(f"Error exporting to HTML: {e}")
            self._show_error_toast(f"Export failed: {str(e)}")

    def _on_export_pdf(self, button):
        """Export as PDF using WebKit print."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Export as PDF")
        dialog.set_initial_name("document.pdf")

        filter_pdf = Gtk.FileFilter()
        filter_pdf.set_name("PDF Files")
        filter_pdf.add_pattern("*.pdf")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_pdf)
        dialog.set_filters(filters)

        dialog.save(self, None, self._on_export_pdf_response)

    def _on_export_pdf_response(self, dialog, result):
        """Handle PDF export response."""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()
                self._generate_pdf(filepath)
        except Exception as e:
            print(f"Error exporting to PDF: {e}")
            self._show_error_toast(f"Export failed: {str(e)}")

    def _generate_pdf(self, filepath):
        """Generate PDF from HTML content."""
        # Create a temporary WebView for PDF generation
        webview = WebKit.WebView()
        html_content = self.get_full_html_document()

        def on_load_finished(web_view, event):
            # Set up print operation
            print_op = WebKit.PrintOperation.new(web_view)
            page_setup = Gtk.PageSetup()
            print_settings = Gtk.PrintSettings()

            print_settings.set(Gtk.PRINT_SETTINGS_OUTPUT_FILE_FORMAT, "pdf")
            print_settings.set(Gtk.PRINT_SETTINGS_OUTPUT_URI, f"file://{filepath}")

            print_op.set_page_setup(page_setup)
            print_op.set_print_settings(print_settings)

            # Run print operation
            result = print_op.run_dialog(self)
            if result == WebKit.PrintOperationResponse.PRINT:
                print(f"Exported to PDF: {filepath}")
                self._show_success_toast("Exported to PDF successfully!")

        webview.connect(
            "load-changed",
            lambda wv, event: on_load_finished(wv, event)
            if event == WebKit.LoadEvent.FINISHED
            else None,
        )
        webview.load_html(html_content, "file:///")

    def _on_export_image(self, button):
        """Export as image (PNG/JPEG/WebP)."""
        formats = ["png", "jpg", "webp"]
        selected_index = self.dropdown_image_format.get_selected()
        format_ext = formats[selected_index]

        dialog = Gtk.FileDialog()
        dialog.set_title("Export as Image")
        dialog.set_initial_name(f"document.{format_ext}")

        filter_img = Gtk.FileFilter()
        filter_img.set_name(f"{format_ext.upper()} Files")
        filter_img.add_pattern(f"*.{format_ext}")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_img)
        dialog.set_filters(filters)

        dialog.save(
            self, None, lambda d, r: self._on_export_image_response(d, r, format_ext)
        )

    def _on_export_image_response(self, dialog, result, format_ext):
        """Handle image export response."""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()
                self._generate_image(filepath, format_ext)
        except Exception as e:
            print(f"Error exporting to image: {e}")
            self._show_error_toast(f"Export failed: {str(e)}")

    def _generate_image(self, filepath, format_ext):
        """Generate image from HTML content using WebKit snapshot."""
        webview = WebKit.WebView()
        html_content = self.get_full_html_document()

        def on_snapshot_ready(source, result, user_data):
            try:
                texture = webview.get_snapshot_finish(result)
                # Save texture as image
                texture.save_to_png(filepath)
                print(f"Exported to {format_ext.upper()}: {filepath}")
                self._show_success_toast(
                    f"Exported to {format_ext.upper()} successfully!"
                )
            except Exception as e:
                print(f"Error saving snapshot: {e}")
                self._show_error_toast(f"Export failed: {str(e)}")

        def on_load_finished(web_view, event):
            if event == WebKit.LoadEvent.FINISHED:
                # Take snapshot of the webview
                webview.get_snapshot(
                    WebKit.SnapshotRegion.FULL_DOCUMENT,
                    WebKit.SnapshotOptions.NONE,
                    None,
                    on_snapshot_ready,
                    None,
                )

        webview.connect("load-changed", on_load_finished)
        webview.load_html(html_content, "file:///")

    def _show_success_toast(self, message):
        """Show success toast."""
        if self.parent_window:
            toast = Adw.Toast.new(message)
            toast.set_timeout(3)
            # Note: You need to add a ToastOverlay to the parent window to use this
            print(message)

    def _show_error_toast(self, message):
        """Show error toast."""
        if self.parent_window:
            toast = Adw.Toast.new(message)
            toast.set_timeout(3)
            print(message)
