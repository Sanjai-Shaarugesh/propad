import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from propad.i18n import _

UI_FILE = "ui/shortcuts_window.ui"


@Gtk.Template(filename=UI_FILE)
class ShortcutsDialog(Adw.Dialog):
    __gtype_name__ = "ShortcutsDialog"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ShortcutsWindow:
    """Keyboard shortcuts dialog wrapper for compatibility."""

    def __init__(self, parent=None):
        """Initialize shortcuts dialog."""
        self.dialog = ShortcutsDialog()
        self.parent = parent

    def present(self):
        """Present the shortcuts dialog."""
        if self.dialog and self.parent:
            self.dialog.present(self.parent)
