import gi
import re

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GLib

UI_FILE = "ui/search_replace.ui"


@Gtk.Template(filename=UI_FILE)
class SearchReplaceBar(Gtk.Box):
    __gtype_name__ = "SearchReplaceBar"

    search_entry = Gtk.Template.Child()
    replace_entry = Gtk.Template.Child()
    replace_revealer = Gtk.Template.Child()
    btn_prev = Gtk.Template.Child()
    btn_next = Gtk.Template.Child()
    btn_case_sensitive = Gtk.Template.Child()
    btn_whole_word = Gtk.Template.Child()
    btn_regex = Gtk.Template.Child()
    btn_close = Gtk.Template.Child()
    btn_replace = Gtk.Template.Child()
    btn_replace_all = Gtk.Template.Child()
    btn_toggle_replace = Gtk.Template.Child()

    def __init__(self, textview, **kwargs):
        if "orientation" not in kwargs:
            kwargs["orientation"] = Gtk.Orientation.VERTICAL
        super().__init__(**kwargs)

        self.textview = textview
        self.buffer = textview.get_buffer()
        self.current_match_tag = None
        self.matches = []
        self.current_match_index = -1

        # Create text tags for highlighting
        self.match_tag = self.buffer.create_tag(
            "search-match", background="#ffeb3b", foreground="#000000"
        )

        self.current_match_tag = self.buffer.create_tag(
            "current-match", background="#ff9800", foreground="#000000"
        )

        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", lambda e: self._find_next())
        self.search_entry.connect("stop-search", lambda e: self.hide())

        self.btn_prev.connect("clicked", lambda b: self._find_prev())
        self.btn_next.connect("clicked", lambda b: self._find_next())
        self.btn_close.connect("clicked", lambda b: self.hide())

        self.btn_replace.connect("clicked", self._on_replace_clicked)
        self.btn_replace_all.connect("clicked", self._on_replace_all_clicked)
        self.btn_toggle_replace.connect("toggled", self._on_toggle_replace)

    def show_search(self):
        """Show search bar only."""
        self.set_visible(True)
        self.replace_revealer.set_reveal_child(False)
        self.btn_toggle_replace.set_active(False)
        self.search_entry.grab_focus()

    def show_replace(self):
        """Show search and replace bar."""
        self.set_visible(True)
        self.replace_revealer.set_reveal_child(True)
        self.btn_toggle_replace.set_active(True)
        self.search_entry.grab_focus()

    def hide(self):
        """Hide the search bar."""
        self.set_visible(False)
        self._clear_highlights()

    def _on_toggle_replace(self, button):
        """Toggle replace bar visibility."""
        self.replace_revealer.set_reveal_child(button.get_active())

    def _on_search_changed(self, entry):
        """Handle search text changes."""
        search_text = entry.get_text()
        if not search_text:
            self._clear_highlights()
            return

        self._find_all_matches(search_text)
        if self.matches:
            self.current_match_index = 0
            self._highlight_current_match()

    def _find_all_matches(self, search_text):
        """Find all matches in the buffer."""
        self._clear_highlights()
        self.matches = []

        if not search_text:
            return

        # Get buffer text
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        text = self.buffer.get_text(start_iter, end_iter, True)

        # Prepare search pattern
        case_sensitive = self.btn_case_sensitive.get_active()
        whole_word = self.btn_whole_word.get_active()
        use_regex = self.btn_regex.get_active()

        try:
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
            else:
                pattern_text = re.escape(search_text)
                if whole_word:
                    pattern_text = r"\b" + pattern_text + r"\b"
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(pattern_text, flags)

            # Find all matches
            for match in pattern.finditer(text):
                start_pos = match.start()
                end_pos = match.end()

                start_iter = self.buffer.get_iter_at_offset(start_pos)
                end_iter = self.buffer.get_iter_at_offset(end_pos)

                self.matches.append((start_iter.copy(), end_iter.copy()))
                self.buffer.apply_tag(self.match_tag, start_iter, end_iter)

        except re.error as e:
            print(f"Regex error: {e}")
            return

    def _highlight_current_match(self):
        """Highlight the current match."""
        if not self.matches or self.current_match_index < 0:
            return

        # Remove previous current match highlighting
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.remove_tag(self.current_match_tag, start, end)

        # Highlight current match
        start_iter, end_iter = self.matches[self.current_match_index]
        self.buffer.apply_tag(self.current_match_tag, start_iter, end_iter)

        # Scroll to current match
        self.textview.scroll_to_iter(start_iter, 0.25, False, 0.0, 0.0)

    def _find_next(self):
        """Find next match."""
        if not self.matches:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        self._highlight_current_match()

    def _find_prev(self):
        """Find previous match."""
        if not self.matches:
            return

        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        self._highlight_current_match()

    def _on_replace_clicked(self, button):
        """Replace current match."""
        if not self.matches or self.current_match_index < 0:
            return

        replace_text = self.replace_entry.get_text()
        start_iter, end_iter = self.matches[self.current_match_index]

        # Replace text
        self.buffer.delete(start_iter, end_iter)
        self.buffer.insert(start_iter, replace_text)

        # Re-find matches
        search_text = self.search_entry.get_text()
        self._find_all_matches(search_text)

        # Move to next match
        if self.matches:
            if self.current_match_index >= len(self.matches):
                self.current_match_index = 0
            self._highlight_current_match()

    def _on_replace_all_clicked(self, button):
        """Replace all matches."""
        if not self.matches:
            return

        replace_text = self.replace_entry.get_text()

        # Replace from end to start to maintain offsets
        for start_iter, end_iter in reversed(self.matches):
            self.buffer.delete(start_iter, end_iter)
            self.buffer.insert(start_iter, replace_text)

        # Re-find matches (should be empty now)
        search_text = self.search_entry.get_text()
        self._find_all_matches(search_text)

    def _clear_highlights(self):
        """Clear all search highlights."""
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        self.buffer.remove_tag(self.match_tag, start, end)
        self.buffer.remove_tag(self.current_match_tag, start, end)
        self.matches = []
        self.current_match_index = -1
