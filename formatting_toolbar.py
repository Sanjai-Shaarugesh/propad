import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gio

UI_FILE = "ui/formatting_toolbar.ui"


@Gtk.Template(filename=UI_FILE)
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

    def __init__(self, textview, parent_window, **kwargs):
        super().__init__(**kwargs)
        self.textview = textview
        self.buffer = textview.get_buffer()
        self.parent_window = parent_window

        # Connect formatting buttons
        self.btn_bold.connect("clicked", lambda b: self._wrap_selection("**", "**"))
        self.btn_italic.connect("clicked", lambda b: self._wrap_selection("*", "*"))
        self.btn_strikethrough.connect(
            "clicked", lambda b: self._wrap_selection("~~", "~~")
        )
        self.btn_code.connect("clicked", lambda b: self._wrap_selection("`", "`"))

        # Connect heading buttons
        self.btn_h1.connect("clicked", lambda b: self._insert_heading("#"))
        self.btn_h2.connect("clicked", lambda b: self._insert_heading("##"))
        self.btn_h3.connect("clicked", lambda b: self._insert_heading("###"))
        self.btn_h4.connect("clicked", lambda b: self._insert_heading("####"))

        # Connect list buttons
        self.btn_bullet_list.connect(
            "clicked", lambda b: self._insert_line_prefix("- ")
        )
        self.btn_numbered_list.connect(
            "clicked", lambda b: self._insert_line_prefix("1. ")
        )
        self.btn_quote.connect("clicked", lambda b: self._insert_line_prefix("> "))
        self.btn_code_block.connect("clicked", self._insert_code_block)

        # Connect insert buttons
        self.btn_link.connect("clicked", self._insert_link)
        self.btn_image.connect("clicked", self._insert_image)
        self.btn_table.connect("clicked", self._show_table_dialog)
        self.btn_mermaid.connect("clicked", self._insert_mermaid)
        self.btn_latex.connect("clicked", self._insert_latex)

    def _wrap_selection(self, prefix, suffix):
        """Wrap selected text with prefix and suffix."""
        bounds = self.buffer.get_selection_bounds()
        if bounds:
            start, end = bounds
            text = self.buffer.get_text(start, end, True)
            self.buffer.delete(start, end)
            self.buffer.insert(start, f"{prefix}{text}{suffix}")
        else:
            # No selection, insert at cursor
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert(cursor, f"{prefix}text{suffix}")
        self.popdown()

    def _insert_heading(self, prefix):
        """Insert heading at current line."""
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        line_start = self.buffer.get_iter_at_line(cursor.get_line())

        # Check if line already has heading
        line_end = line_start.copy()
        line_end.forward_to_line_end()
        line_text = self.buffer.get_text(line_start, line_end, True)

        if line_text.startswith("#"):
            # Replace existing heading
            hash_count = len(line_text) - len(line_text.lstrip("#"))
            end_of_hashes = line_start.copy()
            end_of_hashes.forward_chars(hash_count)
            if line_text[hash_count : hash_count + 1] == " ":
                end_of_hashes.forward_char()
            self.buffer.delete(line_start, end_of_hashes)

        # Insert new heading
        self.buffer.insert(line_start, f"{prefix} ")
        self.popdown()

    def _insert_line_prefix(self, prefix):
        """Insert prefix at beginning of current line."""
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        line_start = self.buffer.get_iter_at_line(cursor.get_line())
        self.buffer.insert(line_start, prefix)
        self.popdown()

    def _insert_code_block(self, button):
        """Insert code block."""
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.buffer.insert(cursor, "```python\n# Your code here\n```\n")
        self.popdown()

    def _insert_link(self, button):
        """Insert link with dialog."""
        dialog = Gtk.Dialog(
            title="Insert Link", transient_for=self.parent_window, modal=True
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Insert", Gtk.ResponseType.OK)

        box = dialog.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        text_label = Gtk.Label(label="Link Text:")
        text_label.set_halign(Gtk.Align.START)
        text_entry = Gtk.Entry()
        text_entry.set_placeholder_text("Click here")

        url_label = Gtk.Label(label="URL:")
        url_label.set_halign(Gtk.Align.START)
        url_entry = Gtk.Entry()
        url_entry.set_placeholder_text("https://example.com")

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
        """Handle link dialog response."""
        if response == Gtk.ResponseType.OK:
            text = text_entry.get_text() or "link"
            url = url_entry.get_text() or "https://"
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert(cursor, f"[{text}]({url})")
        dialog.destroy()

    def _insert_image(self, button):
        """Insert image from file."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Image")

        # Create file filter for images
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Image Files")
        filter_img.add_mime_type("image/*")
        filter_img.add_pattern("*.png")
        filter_img.add_pattern("*.jpg")
        filter_img.add_pattern("*.jpeg")
        filter_img.add_pattern("*.gif")
        filter_img.add_pattern("*.webp")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_img)
        dialog.set_filters(filters)

        dialog.open(self.parent_window, None, self._on_image_selected)
        self.popdown()

    def _on_image_selected(self, dialog, result):
        """Handle image file selection."""
        try:
            file = dialog.open_finish(result)
            if file:
                filepath = file.get_path()
                filename = file.get_basename()
                cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
                self.buffer.insert(cursor, f"![{filename}]({filepath})\n")
        except Exception as e:
            print(f"Error selecting image: {e}")

    def _show_table_dialog(self, button):
        """Show table insertion dialog."""
        table_dialog = TableInsertDialog(self.parent_window, self.buffer)
        table_dialog.present()
        self.popdown()

    def _insert_mermaid(self, button):
        """Insert Mermaid diagram template."""
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        template = """```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```
"""
        self.buffer.insert(cursor, template)
        self.popdown()

    def _insert_latex(self, button):
        """Insert LaTeX math template."""
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        template = "$$\nx = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}\n$$\n"
        self.buffer.insert(cursor, template)
        self.popdown()


class TableInsertDialog(Gtk.Window):
    """Dialog for inserting tables with visual selection."""

    def __init__(self, parent_window, text_buffer):
        super().__init__(title="Insert Table", transient_for=parent_window, modal=True)
        self.text_buffer = text_buffer
        self.selected_rows = 3
        self.selected_cols = 3

        self.set_default_size(400, 450)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(20)
        content_box.set_margin_bottom(20)

        # Label
        label = Gtk.Label(label="Click to select table size:")
        label.set_halign(Gtk.Align.START)
        content_box.append(label)

        # Size label
        self.size_label = Gtk.Label(
            label=f"{self.selected_rows} × {self.selected_cols}"
        )
        self.size_label.add_css_class("title-2")
        content_box.append(self.size_label)

        # Grid for cell selection
        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(4)
        self.grid.set_column_spacing(4)

        self.cells = []
        for row in range(10):
            row_cells = []
            for col in range(10):
                button = Gtk.Button()
                button.set_size_request(30, 30)
                button.add_css_class("flat")
                button.connect("enter", self._on_cell_hover, row, col)
                button.connect("clicked", self._on_cell_clicked, row, col)
                self.grid.attach(button, col, row, 1, 1)
                row_cells.append(button)
            self.cells.append(row_cells)

        content_box.append(self.grid)

        # Insert button
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(12)

        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda b: self.close())

        btn_insert = Gtk.Button(label="Insert Table")
        btn_insert.add_css_class("suggested-action")
        btn_insert.connect("clicked", self._insert_table)

        btn_box.append(btn_cancel)
        btn_box.append(btn_insert)
        content_box.append(btn_box)

        main_box.append(content_box)
        self.set_child(main_box)

        self._update_grid()

    def _on_cell_hover(self, button, row, col):
        """Handle cell hover."""
        self.selected_rows = row + 1
        self.selected_cols = col + 1
        self._update_grid()

    def _on_cell_clicked(self, button, row, col):
        """Handle cell click."""
        self.selected_rows = row + 1
        self.selected_cols = col + 1
        self._update_grid()

    def _update_grid(self):
        """Update grid highlighting."""
        for row in range(10):
            for col in range(10):
                cell = self.cells[row][col]
                if row < self.selected_rows and col < self.selected_cols:
                    cell.add_css_class("accent")
                else:
                    cell.remove_css_class("accent")

        self.size_label.set_label(f"{self.selected_rows} × {self.selected_cols}")

    def _insert_table(self, button):
        """Insert the table into the text buffer."""
        # Create table markdown
        table_lines = []

        # Header row
        header = (
            "| "
            + " | ".join([f"Column {i + 1}" for i in range(self.selected_cols)])
            + " |"
        )
        table_lines.append(header)

        # Separator
        separator = "| " + " | ".join(["---" for _ in range(self.selected_cols)]) + " |"
        table_lines.append(separator)

        # Data rows
        for i in range(self.selected_rows - 1):
            row = "| " + " | ".join(["" for _ in range(self.selected_cols)]) + " |"
            table_lines.append(row)

        table_md = "\n".join(table_lines) + "\n\n"

        # Insert into buffer
        cursor = self.text_buffer.get_iter_at_mark(self.text_buffer.get_insert())
        self.text_buffer.insert(cursor, table_md)

        self.close()
