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

        # Custom callbacks list
        self._text_changed_callbacks = []

        # Connect GTK buffer "changed" signal
        self.buffer.connect("changed", self._on_buffer_changed)

    def _on_buffer_changed(self, buffer):
        """Call all registered callbacks when text changes."""
        for callback in self._text_changed_callbacks:
            callback(self.get_text())

    def connect_text_changed(self, callback):
        """Register a callback for text changes."""
        self._text_changed_callbacks.append(callback)

    def get_text(self):
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        return self.buffer.get_text(start_iter, end_iter, True)

    def set_text(self, text: str):
        """Set text and trigger callbacks."""
        self.buffer.set_text(text)
        for callback in self._text_changed_callbacks:
            callback(text)

    def clear(self):
        self.buffer.set_text("")
        for callback in self._text_changed_callbacks:
            callback("")
