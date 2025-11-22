import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

UI_FILE = "ui/formatting_toolbar.ui"


@Gtk.Template(filename=UI_FILE)
class FormattingToolbar(Gtk.Popover):
    __gtype_name__ = "FormattingToolbar"

    # Text formatting buttons
    btn_bold = Gtk.Template.Child()
    btn_italic = Gtk.Template.Child()
    btn_strikethrough = Gtk.Template.Child()
    btn_code = Gtk.Template.Child()

    # Heading buttons
    btn_h1 = Gtk.Template.Child()
    btn_h2 = Gtk.Template.Child()
    btn_h3 = Gtk.Template.Child()
    btn_h4 = Gtk.Template.Child()

    # List and block buttons
    btn_bullet_list = Gtk.Template.Child()
    btn_numbered_list = Gtk.Template.Child()
    btn_quote = Gtk.Template.Child()
    btn_code_block = Gtk.Template.Child()

    # Insert buttons
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

        # Used by numbered list (fix crash)
        self.offset = 0

        # Connect buttons
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

        self.btn_link.connect("clicked", self._on_insert_link)
        self.btn_image.connect("clicked", self._on_insert_image)
        self.btn_table.connect("clicked", self._on_insert_table)
        self.btn_mermaid.connect("clicked", self._on_insert_mermaid)
        self.btn_latex.connect("clicked", self._on_insert_latex)

    # ─────────────────────────────────────────────
    # WRAPPING
    # ─────────────────────────────────────────────
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

    # ─────────────────────────────────────────────
    # HEADINGS
    # ─────────────────────────────────────────────
    def _insert_heading(self, level):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        line_num = cursor.get_line()
        line_start, _ = self.buffer.get_iter_at_line(line_num)
        line_end, _ = self.buffer.get_iter_at_line(line_num)

        if not line_end.ends_line():
            line_end.forward_to_line_end()

        line_text = self.buffer.get_text(line_start, line_end, True)
        stripped = line_text.lstrip("#").lstrip()

        heading_prefix = "#" * level + " "

        self.buffer.delete(line_start, line_end)
        self.buffer.insert(line_start, heading_prefix + stripped)

        self.popdown()

    # ─────────────────────────────────────────────
    # BULLET LIST (FIXED)
    # ─────────────────────────────────────────────
    def _insert_bullet_list(self):
        try:
            buffer = self.buffer

            # Cursor position
            cursor_mark = buffer.get_insert()
            cursor_iter = buffer.get_iter_at_mark(cursor_mark)

            # Start of line
            line_start = cursor_iter.copy()
            line_start.set_line_offset(0)

            # End of line
            line_end = cursor_iter.copy()
            line_end.forward_to_line_end()

            # Extract text safely
            original_text = buffer.get_text(line_start, line_end, False).strip()

            # Remove existing bullet if present
            if original_text.startswith("• "):
                original_text = original_text[2:]

            # If line empty use placeholder
            if original_text == "":
                original_text = "Item"

            # Build 3 bullet points
            lines = f"- {original_text}\n- {original_text}\n- {original_text}\n"

            # Replace the line
            buffer.delete(line_start, line_end)
            buffer.insert(line_start, lines)

        except Exception as e:
            print("Error inserting bullet list:", e)

    # ─────────────────────────────────────────────
    # NUMBERED LIST (FIXED)
    # ─────────────────────────────────────────────
    def _insert_numbered_list(self):
        try:
            buffer = self.buffer

            # Cursor position
            cursor_mark = buffer.get_insert()
            cursor_iter = buffer.get_iter_at_mark(cursor_mark)

            # Start of line
            line_start = cursor_iter.copy()
            line_start.set_line_offset(0)

            # End of line
            line_end = cursor_iter.copy()
            line_end.forward_to_line_end()

            # Extract text safely
            original_text = buffer.get_text(line_start, line_end, False).strip()

            # Remove existing numbering like "1. "
            if (
                len(original_text) > 2
                and original_text[0].isdigit()
                and original_text[1] == "."
            ):
                original_text = original_text[3:]

            # If line empty use placeholder
            if original_text == "":
                original_text = "Item"

            # Build 3 numbered points
            lines = f"1. {original_text}\n2. {original_text}\n3. {original_text}\n"

            # Replace the line
            buffer.delete(line_start, line_end)
            buffer.insert(line_start, lines)

        except Exception as e:
            print("Error inserting numbered list:", e)

    # ─────────────────────────────────────────────
    # BLOCK QUOTE
    # ─────────────────────────────────────────────
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

    # ─────────────────────────────────────────────
    # CODE BLOCK
    # ─────────────────────────────────────────────
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

    # ─────────────────────────────────────────────
    # LINKS, IMAGE, TABLE, MERMAID, LATEX
    # ─────────────────────────────────────────────
    def _on_insert_link(self, button):
        bounds = self.buffer.get_selection_bounds()
        if bounds:
            start, end = bounds
            text = self.buffer.get_text(start, end, True)
            self.buffer.delete(start, end)
            self.buffer.insert(start, f"[{text}](url)")
        else:
            cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert(cursor, "[text](url)")
        self.popdown()

    def _on_insert_image(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.buffer.insert(cursor, "![alt](url)")
        self.popdown()

    def _on_insert_table(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        table = "| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |\n"
        self.buffer.insert(cursor, table)
        self.popdown()

    def _on_insert_mermaid(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.buffer.insert(cursor, "```mermaid\ngraph TD\nA-->B\n```\n")
        self.popdown()

    def _on_insert_latex(self, button):
        cursor = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.buffer.insert(cursor, "$$ x = {-b \\pm \\sqrt{b^2-4ac} \\over 2a} $$")
        self.popdown()
