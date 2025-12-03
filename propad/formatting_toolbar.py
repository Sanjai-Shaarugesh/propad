import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk, Pango, Gio
import os
import subprocess
from propad.i18n import _


class TableGridSelector(Gtk.Popover):
    """Interactive grid selector for table insertion"""

    def __init__(self, on_table_selected, **kwargs):
        super().__init__(**kwargs)

        self.on_table_selected = on_table_selected
        self.max_rows = 8
        self.max_cols = 8
        self.selected_rows = 0
        self.selected_cols = 0

        self._load_css_from_file()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        title = Gtk.Label(label=_("Insert Table"))
        title.add_css_class("title-label")
        box.append(title)

        grid_frame = Gtk.Frame()
        grid_frame.add_css_class("grid-frame")

        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(0)
        self.grid.set_column_spacing(0)
        self.grid.add_css_class("table-grid")

        self.cells = []
        for row in range(self.max_rows):
            row_cells = []
            for col in range(self.max_cols):
                cell = Gtk.DrawingArea()
                cell.set_size_request(36, 36)
                cell.set_draw_func(self._draw_cell, (row, col))
                cell.add_css_class("grid-cell")

                # Add hover controller
                hover = Gtk.EventControllerMotion()
                hover.connect("enter", self._on_cell_hover, row, col)
                cell.add_controller(hover)

                self.grid.attach(cell, col, row, 1, 1)
                row_cells.append(cell)
            self.cells.append(row_cells)

        click = Gtk.GestureClick()
        click.connect("released", self._on_grid_clicked)
        self.grid.add_controller(click)

        grid_frame.set_child(self.grid)
        box.append(grid_frame)

        dim_display = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dim_display.set_halign(Gtk.Align.CENTER)

        self.rows_label = Gtk.Label(label=_("Rows: 0"))
        self.rows_label.add_css_class("dim-value")
        dim_display.append(self.rows_label)

        # Separator
        separator = Gtk.Label(label=_("×"))
        separator.add_css_class("dim-separator")
        dim_display.append(separator)

        # Columns label
        self.cols_label = Gtk.Label(label=_("Cols: 0"))
        self.cols_label.add_css_class("dim-value")
        dim_display.append(self.cols_label)

        box.append(dim_display)

        self.set_child(box)

    def _load_css_from_file(self):
        css_provider = Gtk.CssProvider()

        css_file_path = "ui/table_selector.css"
        if os.path.exists(css_file_path):
            css_provider.load_from_path(css_file_path)
        else:
            # Fallback to inline CSS
            css_data = """
                /* Title label */
                .title-label {
                    font-size: 14px;
                    font-weight: 600;
                    color: rgba(180, 255, 200, 0.95);
                    margin-bottom: 4px;
                }
                
                /* Grid frame with rounded corners */
                .grid-frame {
                    border-radius: 10px;
                    background: rgba(40, 45, 50, 0.5);
                    border: 1px solid rgba(150, 255, 180, 0.3);
                }
                
                /* Grid styling */
                .table-grid {
                    border-radius: 10px;
                    background: transparent;
                }
                
                /* Individual cell styling */
                .grid-cell {
                    background: transparent;
                }
                
                /* Dimension values (Rows and Cols labels) */
                .dim-value {
                    font-size: 13px;
                    font-weight: 600;
                    color: rgba(200, 255, 220, 1);
                    padding: 4px 10px;
                    background: rgba(100, 200, 120, 0.25);
                    border-radius: 8px;
                    border: 1px solid rgba(120, 220, 140, 0.35);
                }
                
                /* Separator between rows and columns */
                .dim-separator {
                    font-size: 15px;
                    font-weight: 700;
                    color: rgba(150, 255, 180, 0.9);
                }
                
               
            """
            css_provider.load_from_data(css_data.encode())

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _draw_cell(self, area, cr, width, height, data):
        """Draw individual cell with row/column numbers"""
        row, col = data

        # Determine if cell is selected
        is_selected = row < self.selected_rows and col < self.selected_cols

        # Draw cell background
        if is_selected:
            # Transparent green color with opacity for hover effect
            cr.set_source_rgba(0.35, 1.0, 0.55, 0.45)  # Bright green with transparency
        else:
            cr.set_source_rgba(0.18, 0.22, 0.24, 0.7)  # Semi-transparent dark gray

        # Draw rounded corners for corner cells
        radius = 10
        is_top_left = row == 0 and col == 0
        is_top_right = row == 0 and col == self.max_cols - 1
        is_bottom_left = row == self.max_rows - 1 and col == 0
        is_bottom_right = row == self.max_rows - 1 and col == self.max_cols - 1

        if is_top_left or is_top_right or is_bottom_left or is_bottom_right:
            # Draw rounded rectangle for corners
            x, y = 0, 0
            pi = 3.14159

            cr.new_sub_path()

            # Top-left corner
            if is_top_left:
                cr.arc(x + radius, y + radius, radius, pi, 3 * pi / 2)
            else:
                cr.move_to(x, y)

            # Top-right corner
            if is_top_right:
                cr.arc(x + width - radius, y + radius, radius, 3 * pi / 2, 0)
            else:
                cr.line_to(x + width, y)

            # Bottom-right corner
            if is_bottom_right:
                cr.arc(x + width - radius, y + height - radius, radius, 0, pi / 2)
            else:
                cr.line_to(x + width, y + height)

            # Bottom-left corner
            if is_bottom_left:
                cr.arc(x + radius, y + height - radius, radius, pi / 2, pi)
            else:
                cr.line_to(x, y + height)

            cr.close_path()
            cr.fill()
        else:
            # Regular rectangle for middle cells
            cr.rectangle(0, 0, width, height)
            cr.fill()

        # Draw cell border
        cr.set_source_rgba(0.5, 1.0, 0.6, 0.35)  # Light green borders
        cr.set_line_width(1)

        # Draw only right and bottom borders
        if col < self.max_cols - 1:
            cr.move_to(width - 0.5, 0)
            cr.line_to(width - 0.5, height)
            cr.stroke()

        if row < self.max_rows - 1:
            cr.move_to(0, height - 0.5)
            cr.line_to(width, height - 0.5)
            cr.stroke()

        # Draw row and column numbers in cells
        cr.set_source_rgba(0.7, 0.9, 0.8, 0.5)  # Light green-gray text
        if not is_selected:
            cr.set_source_rgba(0.5, 0.6, 0.55, 0.4)  # Dimmer for unselected

        cr.select_font_face("Sans", 0, 0)  # Regular weight
        cr.set_font_size(9)

        # Show row number on first column
        if col == 0:
            text = str(row + 1)
            extents = cr.text_extents(text)
            x = 4
            y = height / 2 + extents.height / 2
            cr.move_to(x, y)
            cr.show_text(text)

        # Show column number on first row
        if row == 0:
            text = str(col + 1)
            extents = cr.text_extents(text)
            x = width - extents.width - 4
            y = 12
            cr.move_to(x, y)
            cr.show_text(text)

    def _on_cell_hover(self, controller, x, y, row, col):
        """Handle cell hover"""
        self.selected_rows = row + 1
        self.selected_cols = col + 1

        # Update dimension labels
        self.rows_label.set_text(f"Rows: {self.selected_rows}")
        self.cols_label.set_text(f"Cols: {self.selected_cols}")

        # Redraw all cells
        for r in range(self.max_rows):
            for c in range(self.max_cols):
                self.cells[r][c].queue_draw()

    def _on_grid_clicked(self, gesture, n_press, x, y):
        """Handle grid click"""
        if self.selected_rows > 0 and self.selected_cols > 0:
            # Generate table markdown
            table = self._generate_table(self.selected_rows, self.selected_cols)
            self.on_table_selected(table)
            self.popdown()

    def _generate_table(self, rows, cols):
        """Generate markdown table"""
        # Header row with letters
        headers = [chr(65 + i) for i in range(cols)]  # A, B, C, ...
        header_line = "| " + " | ".join(headers) + " |"

        # Separator line
        separator = "|" + "|".join(["---" for _ in range(cols)]) + "|"

        # Data rows
        data_lines = []
        for i in range(rows - 1):  # -1 because header is one row
            row_data = [str(i * cols + j + 1) for j in range(cols)]
            data_lines.append("| " + " | ".join(row_data) + " |")

        # Combine all parts
        return "\n".join([header_line, separator] + data_lines) + "\n"


@Gtk.Template(filename="ui/formatting_toolbar.ui")
class FormattingToolbar(Gtk.Popover):
    __gtype_name__ = "FormattingToolbar"

    btn_bold = Gtk.Template.Child()
    btn_italic = Gtk.Template.Child()
    btn_strikethrough = Gtk.Template.Child()
    btn_code = Gtk.Template.Child()

    btn_h1 = Gtk.Template.Child()
    btn_h2 = Gtk.Template.Child()
    btn_h3 = Gtk.Template.Child()
    btn_h4 = Gtk.Template.Child()

    btn_bullet_list = Gtk.Template.Child()
    btn_numbered_list = Gtk.Template.Child()
    btn_quote = Gtk.Template.Child()
    btn_code_block = Gtk.Template.Child()

    btn_link = Gtk.Template.Child()
    btn_image = Gtk.Template.Child()
    btn_table = Gtk.Template.Child()
    btn_mermaid = Gtk.Template.Child()
    btn_latex = Gtk.Template.Child()

    def __init__(self, textview, parent_window=None, **kwargs):
        super().__init__(**kwargs)

        self.textview = textview
        self.parent_window = parent_window
        self.buffer = textview.get_buffer()

        self.offset = 0

        self.table_selector = None

        self.btn_bold.connect("clicked", lambda b: self._wrap_selection("**", "**"))
        self.btn_italic.connect("clicked", lambda b: self._wrap_selection("*", "*"))
        self.btn_strikethrough.connect(
            "clicked", lambda b: self._wrap_selection("~~", "~~")
        )
        self.btn_code.connect("clicked", lambda b: self._wrap_selection("`", "`"))

        self.btn_h1.connect("clicked", lambda b: self._insert_heading(1))
        self.btn_h2.connect("clicked", lambda b: self._insert_heading(2))
        self.btn_h3.connect("clicked", lambda b: self._insert_heading(3))
        self.btn_h4.connect("clicked", lambda b: self._insert_heading(4))

        self.btn_bullet_list.connect("clicked", lambda b: self._insert_bullet_list())
        self.btn_numbered_list.connect(
            "clicked", lambda b: self._insert_numbered_list()
        )
        self.btn_quote.connect("clicked", lambda b: self._insert_block_quote())
        self.btn_code_block.connect("clicked", lambda b: self._insert_code_block())

        self.btn_link.connect("clicked", self._insert_link)
        self.btn_image.connect("clicked", self._insert_image)
        self.btn_table.connect("clicked", self._on_insert_table)
        self.btn_mermaid.connect("clicked", self._on_insert_mermaid)
        self.btn_latex.connect("clicked", self._on_insert_latex)

    def _wrap_selection(self, prefix, suffix):
        """Wrap selected text with prefix & suffix."""
        bounds = self.buffer.get_selection_bounds()
        if bounds:
            start, end = bounds
            text = self.buffer.get_text(start, end, True)
            self.buffer.delete(start, end)
            self.buffer.insert(start, f"{prefix}{text}{suffix}")
        else:
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert(cursor, f"{prefix}text{suffix}")

        self.popdown()

    def _insert_heading(self, level):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        line_num = cursor.get_line()
        _, line_start = self.buffer.get_iter_at_line(line_num)
        _, line_end = self.buffer.get_iter_at_line(line_num)

        if not line_end.ends_line():
            line_end.forward_to_line_end()

        line_text = self.buffer.get_text(line_start, line_end, True)
        stripped = line_text.lstrip("#").lstrip()

        heading_prefix = "#" * level + " "

        self.buffer.delete(line_start, line_end)
        self.buffer.insert(line_start, heading_prefix + stripped)

        self.popdown()

    def _insert_bullet_list(self):
        try:
            buffer = self.buffer

            cursor_mark = buffer.get_insert()
            cursor_iter = buffer.get_iter_at_mark(cursor_mark)

            line_start = cursor_iter.copy()
            line_start.set_line_offset(0)

            line_end = cursor_iter.copy()
            line_end.forward_to_line_end()

            original_text = buffer.get_text(line_start, line_end, False).strip()

            if original_text.startswith("• "):
                original_text = original_text[2:]

            if original_text == "":
                original_text = "Item"

            lines = f"- {original_text}\n- {original_text}\n- {original_text}\n"

            buffer.delete(line_start, line_end)
            buffer.insert(line_start, lines)

        except Exception as e:
            print("Error inserting bullet list:", e)

    def _insert_numbered_list(self):
        try:
            buffer = self.buffer

            cursor_mark = buffer.get_insert()
            cursor_iter = buffer.get_iter_at_mark(cursor_mark)

            line_start = cursor_iter.copy()
            line_start.set_line_offset(0)

            line_end = cursor_iter.copy()
            line_end.forward_to_line_end()

            original_text = buffer.get_text(line_start, line_end, False).strip()

            if (
                len(original_text) > 2
                and original_text[0].isdigit()
                and original_text[1] == "."
            ):
                original_text = original_text[3:]

            if original_text == "":
                original_text = "Item"

            lines = f"1. {original_text}\n2. {original_text}\n3. {original_text}\n"

            buffer.delete(line_start, line_end)
            buffer.insert(line_start, lines)

        except Exception as e:
            print("Error inserting numbered list:", e)

    def _insert_block_quote(self):
        bounds = self.buffer.get_selection_bounds()
        if bounds:
            start, end = bounds
            text = self.buffer.get_text(start, end, True)
            quoted = "\n".join(f"> {l}" for l in text.split("\n"))
            self.buffer.delete(start, end)
            self.buffer.insert(start, quoted)
        else:
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert(cursor, "> Quote here\n")
        self.popdown()

    def _insert_code_block(self):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        bounds = self.buffer.get_selection_bounds()

        if bounds:
            start, end = bounds
            text = self.buffer.get_text(start, end, True)
            self.buffer.delete(start, end)
            self.buffer.insert(start, f"```\n{text}\n```\n")
        else:
            self.buffer.insert(cursor, "```\ncode\n```\n")

        self.popdown()

    def _insert_link(self, button):
        dialog = Gtk.Dialog(
            title=_("Insert Link"), transient_for=self.parent_window, modal=True
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Insert", Gtk.ResponseType.OK)

        box = dialog.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        text_label = Gtk.Label(label=_("Link Text:"))
        text_label.set_halign(Gtk.Align.START)
        text_entry = Gtk.Entry()
        text_entry.set_placeholder_text(_("Click here"))

        url_label = Gtk.Label(label=_("URL:"))
        url_label.set_halign(Gtk.Align.START)
        url_entry = Gtk.Entry()
        url_entry.set_placeholder_text(_("https://example.com"))

        box.append(text_label)
        box.append(text_entry)
        box.append(url_label)
        box.append(url_entry)

        dialog.connect(
            "response", lambda d, r: self._on_link_response(d, r, text_entry, url_entry)
        )
        dialog.present()
        self.popdown()

    def _on_link_response(self, dialog, response, text_entry, url_entry):
        if response == Gtk.ResponseType.OK:
            text = text_entry.get_text() or "link"
            url = url_entry.get_text() or "https://"
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert(cursor, f"[{text}]({url})")
        dialog.destroy()

    def _insert_image(self, button):
        dialog = Gtk.FileChooserDialog(
            title=_("Select Image"),
            transient_for=self.parent_window,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.ACCEPT
        )

        # Image filter
        filter_img = Gtk.FileFilter()
        filter_img.set_name(_("Image Files"))
        filter_img.add_mime_type("image/*")
        for pattern in [
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.gif",
            "*.webp",
            "*.svg",
            "*.bmp",
        ]:
            filter_img.add_pattern(pattern)

        filter_all = Gtk.FileFilter()
        filter_all.set_name(_("All Files"))
        filter_all.add_pattern("*")

        dialog.add_filter(filter_img)
        dialog.add_filter(filter_all)

        try:
            from gi.repository import GLib

            pictures_path = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_PICTURES
            )
            if pictures_path and os.path.exists(pictures_path):
                f = Gio.File.new_for_path(pictures_path)
                dialog.set_current_folder(f)
        except:
            pass

        dialog.connect("response", self._on_image_dialog_response)
        dialog.present()
        self.popdown()

    def _on_image_dialog_response(self, dialog, response):
        """Handle image selection and insert absolute path."""
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file:
                filepath = file.get_path()
                filename = file.get_basename()

                cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
                self.buffer.insert(cursor, f"![{filename}]({filepath})\n")

                print(f"Image inserted: {filepath}")

        dialog.destroy()

    def _on_insert_table(self, button):
        """Show interactive table grid selector"""
        if self.table_selector is None:
            self.table_selector = TableGridSelector(
                on_table_selected=self._insert_table_from_selector
            )
            self.table_selector.set_parent(self.btn_table)

        self.table_selector.popup()

    def _insert_table_from_selector(self, table_markdown):
        """Insert the generated table"""
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.buffer.insert(cursor, table_markdown)
        self.popdown()

    def _on_insert_mermaid(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.buffer.insert(cursor, "```mermaid\ngraph TD\nA-->B\n```\n")
        self.popdown()

    def _on_insert_latex(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.buffer.insert(cursor, "$$ x = {-b \\pm \\sqrt{b^2-4ac} \\over 2a} $$")
        self.popdown()
