import gi
import re

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

UI_FILE = "ui/search_replace.ui"


@Gtk.Template(filename=UI_FILE)
class SearchReplaceBar(Gtk.Box):
    __gtype_name__ = "SearchReplaceBar"

    search_entry = Gtk.Template.Child()
    replace_entry = Gtk.Template.Child()
    btn_prev = Gtk.Template.Child()
    btn_next = Gtk.Template.Child()
    btn_case_sensitive = Gtk.Template.Child()
    btn_whole_word = Gtk.Template.Child()
    btn_regex = Gtk.Template.Child()
    btn_close = Gtk.Template.Child()
    btn_replace = Gtk.Template.Child()
    btn_replace_all = Gtk.Template.Child()
    btn_toggle_replace = Gtk.Template.Child()
    replace_revealer = Gtk.Template.Child()

    def __init__(self, textview, **kwargs):
        if "orientation" not in kwargs:
            kwargs["orientation"] = Gtk.Orientation.VERTICAL
        super().__init__(**kwargs)

        self.textview = textview
        self.buffer = textview.get_buffer()
        self.matches = []
        self.current_match_index = -1

        # Create text tags for highlighting
        self.search_tag = self.buffer.create_tag(
            "search-match", background="yellow", foreground="black"
        )
        self.current_tag = self.buffer.create_tag(
            "current-match", background="orange", foreground="black"
        )

        # Connect signals
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", lambda e: self._on_next_clicked(None))
        self.btn_prev.connect("clicked", self._on_prev_clicked)
        self.btn_next.connect("clicked", self._on_next_clicked)
        self.btn_case_sensitive.connect(
            "toggled", lambda b: self._on_search_changed(None)
        )
        self.btn_whole_word.connect("toggled", lambda b: self._on_search_changed(None))
        self.btn_regex.connect("toggled", lambda b: self._on_search_changed(None))
        self.btn_close.connect("clicked", self._on_close_clicked)
        self.btn_replace.connect("clicked", self._on_replace_clicked)
        self.btn_replace_all.connect("clicked", self._on_replace_all_clicked)
        self.btn_toggle_replace.connect("toggled", self._on_toggle_replace)

    def _on_search_changed(self, entry):
        """Handle search text change."""
        search_text = self.search_entry.get_text()

        # Clear previous highlights
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.remove_tag(self.search_tag, start, end)
        self.buffer.remove_tag(self.current_tag, start, end)

        self.matches = []
        self.current_match_index = -1

        if not search_text:
            return

        # Find all matches
        self._find_matches(search_text)

        # Highlight all matches
        for match_start, match_end in self.matches:
            start_iter = self.buffer.get_iter_at_offset(match_start)
            end_iter = self.buffer.get_iter_at_offset(match_end)
            self.buffer.apply_tag(self.search_tag, start_iter, end_iter)

        # Select first match
        if self.matches:
            self.current_match_index = 0
            self._highlight_current_match()

    def _find_matches(self, search_text):
        """Find all matches in the buffer."""
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        text = self.buffer.get_text(start, end, True)

        case_sensitive = self.btn_case_sensitive.get_active()
        whole_word = self.btn_whole_word.get_active()
        use_regex = self.btn_regex.get_active()

        if use_regex:
            # Use regular expression
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                for match in pattern.finditer(text):
                    self.matches.append((match.start(), match.end()))
            except re.error as e:
                print(f"Regex error: {e}")
        else:
            # Simple text search
            if not case_sensitive:
                text = text.lower()
                search_text = search_text.lower()

            pos = 0
            while True:
                pos = text.find(search_text, pos)
                if pos == -1:
                    break

                # Check whole word
                if whole_word:
                    if pos > 0 and text[pos - 1].isalnum():
                        pos += 1
                        continue
                    if (
                        pos + len(search_text) < len(text)
                        and text[pos + len(search_text)].isalnum()
                    ):
                        pos += 1
                        continue

                self.matches.append((pos, pos + len(search_text)))
                pos += len(search_text)

    def _highlight_current_match(self):
        """Highlight the current match."""
        if not self.matches or self.current_match_index < 0:
            return

        # Remove current tag from all
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.remove_tag(self.current_tag, start, end)

        # Highlight current match
        match_start, match_end = self.matches[self.current_match_index]
        start_iter = self.buffer.get_iter_at_offset(match_start)
        end_iter = self.buffer.get_iter_at_offset(match_end)
        self.buffer.apply_tag(self.current_tag, start_iter, end_iter)

        # Scroll to match
        self.textview.scroll_to_iter(start_iter, 0.1, False, 0.0, 0.0)

    def _on_prev_clicked(self, button):
        """Go to previous match."""
        if not self.matches:
            return

        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        self._highlight_current_match()

    def _on_next_clicked(self, button):
        """Go to next match."""
        if not self.matches:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        self._highlight_current_match()

    def _on_replace_clicked(self, button):
        """Replace current match."""
        if not self.matches or self.current_match_index < 0:
            return

        replace_text = self.replace_entry.get_text()
        match_start, match_end = self.matches[self.current_match_index]

        # Replace text
        start_iter = self.buffer.get_iter_at_offset(match_start)
        end_iter = self.buffer.get_iter_at_offset(match_end)
        self.buffer.delete(start_iter, end_iter)
        self.buffer.insert(start_iter, replace_text)

        # Re-search
        self._on_search_changed(None)

    def _on_replace_all_clicked(self, button):
        """Replace all matches."""
        if not self.matches:
            return

        replace_text = self.replace_entry.get_text()
        search_text = self.search_entry.get_text()

        # Get all text
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        text = self.buffer.get_text(start, end, True)

        # Replace based on options
        case_sensitive = self.btn_case_sensitive.get_active()
        use_regex = self.btn_regex.get_active()

        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                new_text = pattern.sub(replace_text, text)
            except re.error as e:
                print(f"Regex error: {e}")
                return
        else:
            if case_sensitive:
                new_text = text.replace(search_text, replace_text)
            else:
                # Case-insensitive replacement
                import re

                pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                new_text = pattern.sub(replace_text, text)

        # Set new text
        self.buffer.set_text(new_text)

        # Re-search
        self._on_search_changed(None)

    def _on_toggle_replace(self, button):
        """Toggle replace revealer."""
        self.replace_revealer.set_reveal_child(button.get_active())

    def _on_close_clicked(self, button):
        """Close search bar."""
        # Clear highlights
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.remove_tag(self.search_tag, start, end)
        self.buffer.remove_tag(self.current_tag, start, end)

        self.set_visible(False)

    def show_search(self):
        """Show and focus search bar."""
        self.set_visible(True)
        self.search_entry.grab_focus()

    def show_replace(self):
        """Show search and replace."""
        self.set_visible(True)
        self.btn_toggle_replace.set_active(True)
        self.search_entry.grab_focus()
