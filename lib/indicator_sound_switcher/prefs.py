import logging
import os

from gi.repository import Gtk

from . import utils

# Global Preferences dialog instance
_dlg = None


def show_dialog(indicator):
    """Instantiate and run a Preferences dialog."""
    global _dlg

    # If the dialog is already open, just bring it up
    if _dlg is not None:
        _dlg.prefs_dialog.present()

    # Instantiate a new dialog otherwise
    else:
        _dlg = PreferencesDialog(indicator)
        try:
            _dlg.run()
        finally:
            _dlg = None


def quit_dialog():
    """Close the Preferences dialog, is any."""
    if _dlg is not None:
        _dlg.prefs_dialog.response(Gtk.ResponseType.CLOSE)


class PreferencesDialog:
    """Preferences dialog."""

    def __init__(self, indicator):
        """Constructor."""
        self.indicator = indicator

        # Initialise the config
        self.config = indicator.config
        if self.config['devices', None] is None:
            self.config['devices'] = {}

        # Open and parse the XML UI file otherwise
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(os.path.dirname(__file__), 'prefs.glade'))

        # Update widgets
        self._update_widgets()

        # Connect signal handlers
        self.builder.connect_signals(self)

    def __getattr__(self, name):
        """Magic getter method. Registers each object as an attribute on first access."""
        obj = self.builder.get_object(name)
        setattr(self, name, obj)
        return obj

    def run(self):
        """Main routine. Show and run the dialog."""
        self.prefs_dialog.show_all()
        self.prefs_dialog.run()
        self.prefs_dialog.destroy()

    def _update_widgets(self):
        """Update the state of 'top level' widgets."""
        # General page - switches
        self.sw_show_inputs.set_active (self.config['show_inputs',  True])
        self.sw_show_outputs.set_active(self.config['show_outputs', True])

        # Device page - device list
        for idx, card in self.indicator.cards.items():
            # Add a grid
            grid = Gtk.Grid(border_width=12, column_spacing=6, row_spacing=6, hexpand=True)

            # Add a list box row
            row = Gtk.ListBoxRow(child=grid)
            row.card = card

            # Add an icon
            grid.attach(Gtk.Image.new_from_icon_name('yast_soundcard', Gtk.IconSize.MENU), 0, 0, 1, 2)

            # Add a device title label
            grid.attach(utils.lbl_bold(card.get_display_name(), xalign=0), 1, 0,  1, 1)

            # Add a device name label
            grid.attach(Gtk.Label(card.name, xalign=0), 1, 1,  1, 1)

            # Add the grid as a list row
            self.lbx_devices.add(row)

        # Update device and port props widgets
        self.update_dev_props_widgets()
        self.update_port_props_widgets()

    def update_dev_props_widgets(self):
        """Update device props widgets."""
        # Get selected row
        row = self.lbx_devices.get_selected_row()

        # Remove all ports from the ports list box
        for port_row in self.lbx_ports.get_children():
            self.lbx_ports.remove(port_row)

        # If there's a selected row
        if row is not None:
            self.e_device_name.set_text(row.card.display_name)
            for name, port in row.card.ports.items():
                # Add a box for labels
                bx_port = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, border_width=6)
                bx_port.pack_start(utils.lbl_bold(port.get_display_name(), xalign=0), False, False, 0)
                bx_port.pack_start(Gtk.Label(port.name, xalign=0), False, False, 0)

                # Add a port row
                port_row = Gtk.ListBoxRow(child=bx_port)
                port_row.port = port
                self.lbx_ports.add(port_row)

            # Show all rows' widgets
            self.lbx_ports.show_all()

        # Enable widgets
        self.bx_dev_props.set_sensitive(row is not None)

    def update_port_props_widgets(self):
        """Update port props widgets."""
        # Get selected row
        row = self.lbx_ports.get_selected_row()

        # If there's a selected row
        if row is not None:
            self.sw_port_visible.set_active(row.port.display_name is not False)
            self.sw_port_always_avail.set_active(row.port.always_avail)
            self.e_port_name.set_text(row.port.display_name)
            #TODO self.cb_port_pref_profile.

        # Enable widgets
        self.g_port_props.set_sensitive(row is not None)

    def on_close(self, *args):
        """Signal handler: dialog Close button clicked."""
        logging.debug('PreferencesDialog.on_close()')
        self.prefs_dialog.response(Gtk.ResponseType.CLOSE)

    def on_device_row_selected(self, list_box: Gtk.ListBox, row: Gtk.ListBoxRow):
        """Signal handler: devices list box row (un)selected."""
        logging.debug('PreferencesDialog.on_device_row_selected()')
        self.update_dev_props_widgets()

    def on_port_row_selected(self, list_box: Gtk.ListBox, row: Gtk.ListBoxRow):
        """Signal handler: ports list box row (un)selected."""
        logging.debug('PreferencesDialog.on_port_row_selected()')
        self.update_port_props_widgets()

    def on_show_inputs_switched(self, widget, data):
        """Signal handler: Show inputs switch changed."""
        logging.debug('PreferencesDialog.on_show_inputs_switched(%s)', widget.get_active())
        self.indicator.config['show_inputs'] = widget.get_active()
        self.indicator.on_refresh()

    def on_show_outputs_switched(self, widget, data):
        """Signal handler: Show outputs switch changed."""
        logging.debug('PreferencesDialog.on_show_outputs_switched(%s)', widget.get_active())
        self.indicator.config['show_outputs'] = widget.get_active()
        self.indicator.on_refresh()

    def on_device_name_changed(self, entry: Gtk.Entry):
        """Signal handler: Device name entry text changed."""
        logging.debug('PreferencesDialog.on_device_name_changed(`%s`)', entry.get_text())
        row = self.lbx_devices.get_selected_row()
        if row:
            self.config['devices'][row.card.name]['name'] = entry.get_text()
        self.indicator.on_refresh()

    @staticmethod
    def on_entry_clear_click(entry, icon_pos, event):
        """Event handler: click on the clear text icon in a text entry."""
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            entry.set_text('')
