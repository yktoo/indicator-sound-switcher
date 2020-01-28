"""Various utility functions."""
from gi.repository import Gtk, Gdk


def lbl_markup(markup: str, **props) -> Gtk.Label:
    """Create and return a new label widget with the given markup."""
    lbl = Gtk.Label(**props)
    lbl.set_markup(markup)
    return lbl


def lbl_bold(text: str, **props) -> Gtk.Label:
    """Create and return a new label widget with bold text."""
    return lbl_markup('<b>{}</b>'.format(text), **props)


def labeled_widget(label: str, widget: Gtk.Widget, resizable: bool = True) -> Gtk.Box:
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


def get_key_name(state: Gdk.ModifierType, keyval: int) -> str:
    """Decode the provided state and key value and return a human-readable name for the keyboard shortcut.
    :param state: modifier state of the keyboard shortcut
    :param keyval: keyval of the keyboard shortcut
    :return: string representation of the shortcut
    """
    keys = []
    if state & Gdk.ModifierType.META_MASK:
        keys.append('Meta')
    if state & Gdk.ModifierType.SUPER_MASK:
        keys.append('Super')
    if state & Gdk.ModifierType.HYPER_MASK:
        keys.append('Hyper')
    if state & Gdk.ModifierType.SHIFT_MASK:
        keys.append('Shift')
    if state & Gdk.ModifierType.CONTROL_MASK:
        keys.append('Ctrl')
    if state & Gdk.ModifierType.MOD1_MASK:
        keys.append('Alt')
    keys.append(Gdk.keyval_name(Gdk.keyval_to_upper(keyval)))
    return '+'.join(keys)
