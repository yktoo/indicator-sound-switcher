"""Various utility functions."""
from gi.repository import Gtk


def lbl_markup(markup: str, **props) -> Gtk.Label:
    """Create and return a new label widget with the given markup."""
    lbl = Gtk.Label(**props)
    lbl.set_markup(markup)
    return lbl


def lbl_bold(text: str, **props) -> Gtk.Label:
    """Create and return a new label widget with bold text."""
    return lbl_markup('<b>{}</b>'.format(text), **props)


def labeled_widget(label: str, widget: Gtk.Widget, resizable: bool=True) -> Gtk.Box:
    """Create and return a new horizontal box encapsulating a label and the given widget.
    :param label: label text
    :param widget: widget to get labeled
    :param resizable: whether the widget is to be resizable
    :return: the created box widget
    """
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    box.pack_start(lbl_bold(label, xalign=0), False, True, 0)
    box.pack_end(widget, resizable, True, 0)
    return box
