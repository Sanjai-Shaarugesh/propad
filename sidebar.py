import gi

gi.require_version(namespace="Gtk", version="4.0")

from gi.repository import Gtk

UI_FILE = "ui/sidebar.ui"


@Gtk.Template(filename=UI_FILE)
class SidebarWidget(Gtk.Box):
    __gtype_name__ = "SidebarWidget"

    textview = Gtk.Template.Child()

    def __init__(self, **kwargs):
        if "orientation" not in kwargs:
            kwargs["orientation"] = Gtk.Orientation.VERTICAL
        super().__init__(**kwargs)

        self.buffer = self.textview.get_buffer()

    def get_text(self):
        """Get the current text from the TextView."""
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        return self.buffer.get_text(start_iter, end_iter, True)

    def set_text(self, text: str):
        """Set text in the TextView."""
        self.buffer.set_text(text)

    def clear(self):
        """Clear the TextView."""
        self.buffer.set_text("")
