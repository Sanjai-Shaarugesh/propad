import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
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

        # Headings
        self.btn_h1.connect("clicked", lambda b: self._insert_heading("#"))
        self.btn_h2.connect("clicked", lambda b: self._insert_heading("##"))
        self.btn_h3.connect("clicked", lambda b: self._insert_heading("###"))
        self.btn_h4.connect("clicked", lambda b: self._insert_heading("####"))

        # Lists & blocks
        self.btn_bullet_list.connect(
            "clicked", lambda b: self._insert_line_prefix("- ")
        )
        self.btn_numbered_list.connect(
            "clicked", lambda b: self._insert_line_prefix("1. ")
        )
        self.btn_quote.connect("clicked", lambda b: self._insert_line_prefix("> "))
        self.btn_code_block.connect("clicked", self._insert_code_block)

        # Insert
        self.btn_link.connect("clicked", self._insert_link)
        self.btn_image.connect("clicked", self._insert_image)
        self.btn_table.connect("clicked", self._show_table_dialog)
        self.btn_mermaid.connect("clicked", self._insert_mermaid)
        self.btn_latex.connect("clicked", self._insert_latex)

    # ---------------- Formatting functions ----------------

    def _wrap_selection(self, prefix, suffix):
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

    def _insert_heading(self, prefix):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        line_start = self.buffer.get_iter_at_line(cursor.get_line())
        line_end = line_start.copy()
        line_end.forward_to_line_end()
        line_text = self.buffer.get_text(line_start, line_end, True)

        if line_text.startswith("#"):
            hash_count = len(line_text) - len(line_text.lstrip("#"))
            end_of_hashes = line_start.copy()
            end_of_hashes.forward_chars(hash_count)
            if line_text[hash_count : hash_count + 1] == " ":
                end_of_hashes.forward_char()
            self.buffer.delete(line_start, end_of_hashes)

        self.buffer.insert(line_start, f"{prefix} ")
        self.popdown()

    def _insert_line_prefix(self, prefix):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        line_start = self.buffer.get_iter_at_line(cursor.get_line())
        self.buffer.insert(line_start, prefix)
        self.popdown()

    def _insert_code_block(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.buffer.insert(cursor, "```bash\n\n```\n")
        self.popdown()

    def _insert_link(self, button):
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
        if response == Gtk.ResponseType.OK:
            text = text_entry.get_text() or "link"
            url = url_entry.get_text() or "https://"
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert(cursor, f"[{text}]({url})")
        dialog.destroy()

    def _insert_image(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Image")

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
        table_dialog = TableInsertDialog(self.parent_window, self.buffer)
        table_dialog.present()
        self.popdown()

    def _insert_mermaid(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        template = """```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```\n"""
        self.buffer.insert(cursor, template)
        self.popdown()

    def _insert_latex(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        template = "$$\nx = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}\n$$\n"
        self.buffer.insert(cursor, template)
        self.popdown()


# ---------------- Table Dialog ----------------


class TableInsertDialog(Gtk.Window):
    # Table alignment styles
    ALIGN_LEFT = "left"
    ALIGN_CENTER = "center"
    ALIGN_RIGHT = "right"

    def __init__(self, parent_window, text_buffer):
        super().__init__(title="Insert Table", transient_for=parent_window, modal=True)
        self.text_buffer = text_buffer
        self.selected_rows = 3
        self.selected_cols = 5
        self.current_alignment = self.ALIGN_CENTER

        # Store cell data
        self.cell_data = {}  # {(row, col): "text"}

        self.set_default_size(500, 550)

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_start(30)
        content_box.set_margin_end(30)
        content_box.set_margin_top(30)
        content_box.set_margin_bottom(30)
        content_box.set_halign(Gtk.Align.CENTER)

        # Overlay for grid + label
        overlay = Gtk.Overlay()

        # Grid container with custom styling
        grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        grid_box.add_css_class("table-grid-container")

        # Grid
        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(4)
        self.grid.set_column_spacing(4)
        self.grid.set_halign(Gtk.Align.CENTER)
        self.grid.set_valign(Gtk.Align.CENTER)
        self.grid.set_margin_start(20)
        self.grid.set_margin_end(20)
        self.grid.set_margin_top(20)
        self.grid.set_margin_bottom(20)

        self.cells = []

        for row in range(10):
            row_cells = []
            for col in range(10):
                drawing_area = Gtk.DrawingArea()
                drawing_area.set_size_request(28, 28)
                drawing_area.set_draw_func(self._draw_cell, row, col)

                event_controller = Gtk.EventControllerMotion()
                event_controller.connect("enter", self._on_cell_hover, row, col)
                drawing_area.add_controller(event_controller)

                gesture = Gtk.GestureClick()
                gesture.connect("pressed", self._on_cell_clicked, row, col)
                drawing_area.add_controller(gesture)

                self.grid.attach(drawing_area, col, row, 1, 1)
                row_cells.append(drawing_area)
            self.cells.append(row_cells)

        grid_box.append(self.grid)
        overlay.set_child(grid_box)

        # Size label overlay
        self.size_label = Gtk.Label(
            label=f"{self.selected_rows} × {self.selected_cols}"
        )
        self.size_label.add_css_class("table-size-label")
        self.size_label.set_halign(Gtk.Align.CENTER)
        self.size_label.set_valign(Gtk.Align.CENTER)
        overlay.add_overlay(self.size_label)

        content_box.append(overlay)

        # Table Style Section
        style_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        style_label = Gtk.Label(label="<b>Table Alignment</b>")
        style_label.set_use_markup(True)
        style_label.set_halign(Gtk.Align.START)
        style_box.append(style_label)

        # Alignment buttons
        align_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        align_box.set_halign(Gtk.Align.CENTER)

        self.btn_align_left = Gtk.ToggleButton(label="← Left")
        self.btn_align_center = Gtk.ToggleButton(label="↔ Center")
        self.btn_align_right = Gtk.ToggleButton(label="→ Right")

        # Set center as default
        self.btn_align_center.set_active(True)

        # Connect signals
        self.btn_align_left.connect(
            "toggled", self._on_alignment_changed, self.ALIGN_LEFT
        )
        self.btn_align_center.connect(
            "toggled", self._on_alignment_changed, self.ALIGN_CENTER
        )
        self.btn_align_right.connect(
            "toggled", self._on_alignment_changed, self.ALIGN_RIGHT
        )

        align_box.append(self.btn_align_left)
        align_box.append(self.btn_align_center)
        align_box.append(self.btn_align_right)

        style_box.append(align_box)
        content_box.append(style_box)

        # Quick Templates Section
        template_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        template_label = Gtk.Label(label="<b>Quick Templates</b>")
        template_label.set_use_markup(True)
        template_label.set_halign(Gtk.Align.START)
        template_box.append(template_label)

        template_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        template_buttons.set_halign(Gtk.Align.CENTER)

        btn_data = Gtk.Button(label="📊 Data")
        btn_data.set_tooltip_text("3×4 table for data")
        btn_data.connect("clicked", lambda b: self._apply_template("data"))

        btn_comparison = Gtk.Button(label="⚖️ Compare")
        btn_comparison.set_tooltip_text("2-column comparison")
        btn_comparison.connect("clicked", lambda b: self._apply_template("compare"))

        btn_schedule = Gtk.Button(label="📅 Schedule")
        btn_schedule.set_tooltip_text("7-day schedule")
        btn_schedule.connect("clicked", lambda b: self._apply_template("schedule"))

        btn_pricing = Gtk.Button(label="💰 Pricing")
        btn_pricing.set_tooltip_text("Pricing table")
        btn_pricing.connect("clicked", lambda b: self._apply_template("pricing"))

        template_buttons.append(btn_data)
        template_buttons.append(btn_comparison)
        template_buttons.append(btn_schedule)
        template_buttons.append(btn_pricing)

        template_box.append(template_buttons)
        content_box.append(template_box)

        # Button box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(10)

        btn_edit = Gtk.Button(label="Edit Cells")
        btn_edit.set_size_request(100, -1)
        btn_edit.connect("clicked", self._show_cell_editor)

        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.set_size_request(100, -1)
        btn_cancel.connect("clicked", lambda b: self.close())

        btn_insert = Gtk.Button(label="Insert")
        btn_insert.set_size_request(100, -1)
        btn_insert.add_css_class("suggested-action")
        btn_insert.connect("clicked", self._insert_table)

        btn_box.append(btn_edit)
        btn_box.append(btn_cancel)
        btn_box.append(btn_insert)

        content_box.append(btn_box)
        main_box.append(content_box)
        self.set_child(main_box)

        # Apply custom CSS
        self._apply_custom_css()
        self._update_grid()

    def _apply_custom_css(self):
        """Apply custom CSS for the table grid styling"""
        css_provider = Gtk.CssProvider()
        css = """
        .table-grid-container {
            background-color: rgba(40, 44, 52, 0.95);
            border-radius: 12px;
            padding: 10px;
        }
        
        .table-size-label {
            font-size: 24px;
            font-weight: bold;
            color: rgba(255, 255, 255, 0.9);
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
        }
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _on_alignment_changed(self, button, alignment):
        """Handle alignment button toggle"""
        if button.get_active():
            self.current_alignment = alignment
            # Unset other buttons
            if alignment != self.ALIGN_LEFT:
                self.btn_align_left.set_active(False)
            if alignment != self.ALIGN_CENTER:
                self.btn_align_center.set_active(False)
            if alignment != self.ALIGN_RIGHT:
                self.btn_align_right.set_active(False)

    def _apply_template(self, template_type):
        """Apply a predefined table template"""
        self.cell_data.clear()

        if template_type == "data":
            self.selected_rows = 4
            self.selected_cols = 4
            headers = ["ID", "Name", "Value", "Status"]
            for col, header in enumerate(headers):
                self.cell_data[(0, col)] = header

        elif template_type == "compare":
            self.selected_rows = 6
            self.selected_cols = 2
            self.cell_data[(0, 0)] = "Feature"
            self.cell_data[(0, 1)] = "Description"
            features = ["Speed", "Cost", "Quality", "Support", "Ease of Use"]
            for row, feature in enumerate(features, 1):
                self.cell_data[(row, 0)] = feature

        elif template_type == "schedule":
            self.selected_rows = 4
            self.selected_cols = 8
            days = ["Time", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for col, day in enumerate(days):
                self.cell_data[(0, col)] = day

        elif template_type == "pricing":
            self.selected_rows = 6
            self.selected_cols = 4
            plans = ["Feature", "Basic", "Pro", "Enterprise"]
            for col, plan in enumerate(plans):
                self.cell_data[(0, col)] = plan
            features = ["Price", "Users", "Storage", "Support", "API Access"]
            for row, feature in enumerate(features, 1):
                self.cell_data[(row, 0)] = feature

        self._update_grid()

    def _draw_cell(self, area, cr, width, height, row, col):
        """Custom draw function for each cell"""
        is_selected = row < self.selected_rows and col < self.selected_cols

        if is_selected:
            cr.set_source_rgba(0.30, 0.69, 0.49, 1.0)  # Green
        else:
            cr.set_source_rgba(0.25, 0.27, 0.31, 1.0)  # Dark gray

        # Draw rounded rectangle
        radius = 4
        cr.arc(radius, radius, radius, 3.14159, 3.14159 * 1.5)
        cr.arc(width - radius, radius, radius, 3.14159 * 1.5, 0)
        cr.arc(width - radius, height - radius, radius, 0, 3.14159 * 0.5)
        cr.arc(radius, height - radius, radius, 3.14159 * 0.5, 3.14159)
        cr.close_path()
        cr.fill()

    def _on_cell_hover(self, controller, x, y, row, col):
        self.selected_rows = row + 1
        self.selected_cols = col + 1
        self._update_grid()

    def _on_cell_clicked(self, gesture, n_press, x, y, row, col):
        if (row + 1) == self.selected_rows and (col + 1) == self.selected_cols:
            self._insert_table()
        else:
            self.selected_rows = row + 1
            self.selected_cols = col + 1
            self._update_grid()

    def _show_cell_editor(self, button):
        """Show cell editor dialog"""
        editor_dialog = Gtk.Window(
            title=f"Edit Table ({self.selected_rows} × {self.selected_cols})",
            transient_for=self,
            modal=True,
        )
        editor_dialog.set_default_size(600, 500)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        editor_dialog.set_titlebar(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_margin_start(20)
        scrolled.set_margin_end(20)
        scrolled.set_margin_top(20)
        scrolled.set_margin_bottom(20)

        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)

        self.entry_widgets = {}
        for row in range(self.selected_rows):
            for col in range(self.selected_cols):
                entry = Gtk.Entry()
                entry.set_size_request(120, -1)

                if row == 0:
                    placeholder = f"Column {col + 1}"
                else:
                    placeholder = f"Cell ({row + 1},{col + 1})"

                current_text = self.cell_data.get((row, col), "")
                if current_text:
                    entry.set_text(current_text)
                else:
                    entry.set_placeholder_text(placeholder)

                grid.attach(entry, col, row, 1, 1)
                self.entry_widgets[(row, col)] = entry

        scrolled.set_child(grid)
        main_box.append(scrolled)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_start(20)
        btn_box.set_margin_end(20)
        btn_box.set_margin_bottom(20)

        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda b: editor_dialog.close())

        btn_apply = Gtk.Button(label="Apply")
        btn_apply.add_css_class("suggested-action")
        btn_apply.connect("clicked", lambda b: self._apply_cell_edits(editor_dialog))

        btn_box.append(btn_cancel)
        btn_box.append(btn_apply)

        main_box.append(btn_box)
        editor_dialog.set_child(main_box)
        editor_dialog.present()

    def _apply_cell_edits(self, editor_dialog):
        """Apply edits from the cell editor"""
        for (row, col), entry in self.entry_widgets.items():
            text = entry.get_text()
            if text:
                self.cell_data[(row, col)] = text
            elif (row, col) in self.cell_data:
                del self.cell_data[(row, col)]
        editor_dialog.close()

    def _update_grid(self):
        """Update grid appearance and size label"""
        for row in range(10):
            for col in range(10):
                self.cells[row][col].queue_draw()

        self.size_label.set_label(f"{self.selected_rows} × {self.selected_cols}")

    def _get_separator_line(self):
        """Get the separator line based on current alignment"""
        if self.current_alignment == self.ALIGN_LEFT:
            separator = ":---"
        elif self.current_alignment == self.ALIGN_RIGHT:
            separator = "---:"
        else:  # CENTER
            separator = ":---:"

        separators = [separator for _ in range(self.selected_cols)]
        return "| " + " | ".join(separators) + " |"

    def _insert_table(self, button=None):
        """Insert properly formatted Markdown table"""
        table_lines = []

        # Header row
        header_cells = []
        for col in range(self.selected_cols):
            cell_text = self.cell_data.get((0, col), f"Column {col + 1}")
            header_cells.append(cell_text)

        header = "| " + " | ".join(header_cells) + " |"
        table_lines.append(header)

        # Separator row with alignment
        table_lines.append(self._get_separator_line())

        # Data rows
        for row in range(1, self.selected_rows):
            row_cells = []
            for col in range(self.selected_cols):
                cell_text = self.cell_data.get((row, col), "")
                row_cells.append(cell_text)
            row_line = "| " + " | ".join(row_cells) + " |"
            table_lines.append(row_line)

        # Add blank line before and after
        table_md = "\n" + "\n".join(table_lines) + "\n\n"

        # Insert at cursor
        self.text_buffer.insert_at_cursor(table_md, len(table_md))

        self.close()
