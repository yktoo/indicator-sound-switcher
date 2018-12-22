import logging
import os
from threading import Timer

from gi.repository import Gtk

from . import utils
from .config import Config


class PreferencesDialog:
    """Preferences dialog."""

    # Preferences dialog singleton
    _dlg = None

    @classmethod
    def show(cls, indicator):
        """Instantiate and run a Preferences dialog."""
        # If the dialog is already open, just bring it up
        if cls._dlg is not None:
            cls._dlg.prefs_dialog.present()

        # Instantiate a new dialog otherwise
        else:
            cls._dlg = PreferencesDialog(indicator)
            try:
                cls._dlg.run()
            finally:
                cls._dlg = None

    @classmethod
    def quit(cls):
        """Close the Preferences dialog, is any."""
        if cls._dlg is not None:
            cls._dlg.prefs_dialog.response(Gtk.ResponseType.CLOSE)

    def __init__(self, indicator):
        """Constructor."""
        self.indicator = indicator
        self.refresh_timer = None

        # Open and parse the XML UI file otherwise
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(os.path.dirname(__file__), 'prefs.glade'))

        # Update widgets
        self.updating_widgets = 0
        self.update_widgets()

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

    def _indicator_refresh_cb(self):
        """Delayed indicator refresh callback."""
        self.refresh_timer = None
        self.indicator.on_refresh()

    def schedule_refresh(self):
        """(Re)schedule a delayed indicator refresh."""
        # Kill the existing timer, if any
        if self.refresh_timer:
            self.refresh_timer.cancel()

        # Schedule a refresh after 2 seconds
        self.refresh_timer = Timer(2.0, self._indicator_refresh_cb)
        self.refresh_timer.start()

    def update_widgets(self):
        """Update the state of 'top level' widgets."""
        # Lock signal handlers
        self.updating_widgets += 1

        # General page - switches
        self.sw_show_inputs.set_active (self.indicator.config['show_inputs',  True])
        self.sw_show_outputs.set_active(self.indicator.config['show_outputs', True])

        # Device page - device list
        for card in self.indicator.cards.values():
            # Add a grid
            grid = Gtk.Grid(border_width=12, column_spacing=6, row_spacing=6, hexpand=True)

            # Add a list box row
            row = Gtk.ListBoxRow(child=grid)

            # Store device's name, ports and profiles as additional attributes in the row
            row.device_name = card.name
            row.device_ports = {
                p.name: {
                    'display_name': p.get_display_name(),
                    'is_output':    p.is_output,
                    'is_available': p.is_available,
                } for p in card.ports.values()
            }
            row.device_profiles = {p.name: p.description for p in card.profiles.values()}

            # Add an icon
            grid.attach(Gtk.Image.new_from_icon_name('yast_soundcard', Gtk.IconSize.MENU), 0, 0, 1, 2)

            # Add a device title label
            grid.attach(utils.lbl_bold(card.get_descriptive_name(), xalign=0), 1, 0,  1, 1)

            # Add a device name label
            grid.attach(Gtk.Label(card.name, xalign=0), 1, 1,  1, 1)

            # Add the row to the list box
            self.lbx_devices.add(row)

        # Update device and port props widgets
        self.update_dev_props_widgets()
        self.update_port_props_widgets()

        # Unlock signal handlers
        self.updating_widgets -= 1

    def update_dev_props_widgets(self):
        """Update device props widgets."""
        # Lock signal handlers
        self.updating_widgets += 1

        # Get selected row
        row = self.lbx_devices.get_selected_row()

        # Remove all ports from the ports list box
        for port_row in self.lbx_ports.get_children():
            self.lbx_ports.remove(port_row)

        # If there's a selected row
        if row is None:
            # Remove all profiles from port's preferred profile combobox
            self.cb_port_pref_profile.remove_all()

        else:
            device_cfg = self.get_current_device_config()
            self.e_device_name.set_text(device_cfg['name', ''])

            # Iterate through device's ports
            for name, port in row.device_ports.items():
                # Add a grid
                grid = Gtk.Grid(border_width=12, column_spacing=6, row_spacing=6, hexpand=True)

                # Add a list box row
                port_row = Gtk.ListBoxRow(child=grid)
                port_row.port_name = name

                # Add an icon
                grid.attach(
                    Gtk.Image.new_from_icon_name('gtk-ok' if port['is_available'] else 'gtk-no', Gtk.IconSize.MENU),
                    0, 0, 1, 2)

                # Add a port title label
                grid.attach(
                    utils.lbl_bold(
                        '{}: {}'.format(_('Out') if port['is_output'] else _('In'), port['display_name']),
                        xalign=0),
                    1, 0, 1, 1)

                # Add a port name label
                grid.attach(Gtk.Label(name, xalign=0), 1, 1,  1, 1)

                # Add the row to the list box
                self.lbx_ports.add(port_row)

            # Show all rows' widgets
            self.lbx_ports.show_all()

            # Update port's preferred profile combobox (technically it's a port's property, but profiles are defined by
            # the port's device)
            for name, desc in row.device_profiles.items():
                self.cb_port_pref_profile.append_text('{} ({})'.format(desc, name))

        # Enable widgets
        self.bx_dev_props.set_sensitive(row is not None)

        # Unlock signal handlers
        self.updating_widgets -= 1

    def update_port_props_widgets(self):
        """Update port properties widgets."""
        # Lock signal handlers
        self.updating_widgets += 1

        # Get selected device's config and port row
        device_cfg = self.get_current_device_config()
        row = self.lbx_ports.get_selected_row()

        # If there's a selected row
        if device_cfg is not None and row is not None:
            port_cfg = device_cfg['ports'][row.port_name]
            cfg_is_config = isinstance(port_cfg, Config)

            # A port is visible unless it's config is set to False
            self.sw_port_visible.set_active(port_cfg is not False)

            # Whether the port is always available
            self.sw_port_always_avail.set_active(cfg_is_config and port_cfg['always_available', False])

            # Port's name can be its config (if it's a str) or the value of its 'name' attribute
            if type(port_cfg) is str:
                pname = port_cfg
            elif cfg_is_config:
                pname = port_cfg['name', '']
            else:
                pname = ''
            self.e_port_name.set_text(pname)

            # Port's preferred profile
            # TODO select correct item

        # Enable widgets
        self.enable_port_props_widgets()

        # Unlock signal handlers
        self.updating_widgets -= 1

    def enable_port_props_widgets(self):
        """Update enabled state of port properties widgets."""
        # Visible switch
        self.g_port_props.set_sensitive(self.lbx_ports.get_selected_row() is not None)

        # Other widgets
        b = self.sw_port_visible.get_active()
        for w in {self.sw_port_always_avail, self.e_port_name, self.cb_port_pref_profile}:
            w.set_sensitive(b)

    def get_current_device_config(self):
        """Fetch and return the Config object that corresponds to the currently selected device.
        :return: device Config instance or None if there's no device selected.
        """
        row = self.lbx_devices.get_selected_row()
        return self.indicator.config['devices'][row.device_name] if row is not None else None

    def get_current_port_config(self):
        """Fetch and return the Config object that corresponds to the currently selected device port. Enforces that it's
        a Config object (not str or False).
        :return: port Config instance or None if there's no port selected.
        """
        device_cfg = self.get_current_device_config()
        port_cfg = None
        if device_cfg is not None:
            row = self.lbx_ports.get_selected_row()
            if row is not None:
                # Make sure the port's config is a Config instance (it can also be a string or False)
                port_cfg = device_cfg['ports'][row.port_name]
                if type(port_cfg) is not Config:
                    # Migrate port name, if any, into a config attribute
                    port_cfg = {'name': port_cfg if type(port_cfg) is str else ''}
                    device_cfg['ports'][row.port_name] = port_cfg
        return port_cfg

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
        if self.updating_widgets > 0:
            return
        val = widget.get_active()
        logging.debug('PreferencesDialog.on_show_inputs_switched(%s)', val)
        self.indicator.config['show_inputs'] = val
        self.schedule_refresh()

    def on_show_outputs_switched(self, widget, data):
        """Signal handler: Show outputs switch changed."""
        if self.updating_widgets > 0:
            return
        val = widget.get_active()
        logging.debug('PreferencesDialog.on_show_outputs_switched(%s)', val)
        self.indicator.config['show_outputs'] = val
        self.schedule_refresh()

    def on_device_name_changed(self, entry: Gtk.Entry):
        """Signal handler: Device name entry text changed."""
        if self.updating_widgets > 0:
            return
        val = entry.get_text()
        logging.debug('PreferencesDialog.on_device_name_changed(`%s`)', val)
        cfg = self.get_current_device_config()
        if cfg is not None:
            cfg['name'] = val
            self.schedule_refresh()

    def on_port_visible_switched(self, widget, data):
        """Signal handler: Port visible switch changed."""
        if self.updating_widgets > 0:
            return
        val = widget.get_active()
        logging.debug('PreferencesDialog.on_port_visible_switched(%s)', val)

        # Fetch current device config and the current port row
        device_cfg = self.get_current_device_config()
        row = self.lbx_ports.get_selected_row()
        if device_cfg is not None and row is not None:
            # If the port is visible, set its config to an empty Config instance, otherwise to False
            device_cfg['ports'][row.port_name] = {} if val else False

            # Enable widgets
            self.enable_port_props_widgets()

            # Schedule indicator update
            self.schedule_refresh()

    def on_port_always_avail_switched(self, widget, data):
        """Signal handler: Port always available switch changed."""
        if self.updating_widgets > 0:
            return
        val = widget.get_active()
        logging.debug('PreferencesDialog.on_port_always_avail_switched(%s)', val)
        cfg = self.get_current_port_config()
        if cfg is not None:
            cfg['always_available'] = val
            self.schedule_refresh()

    def on_port_name_changed(self, entry: Gtk.Entry):
        """Signal handler: Port name entry text changed."""
        if self.updating_widgets > 0:
            return
        val = entry.get_text()
        logging.debug('PreferencesDialog.on_port_name_changed(`%s`)', val)
        cfg = self.get_current_port_config()
        if cfg is not None:
            cfg['name'] = val
            self.schedule_refresh()

    @staticmethod
    def on_entry_clear_click(entry, icon_pos, event):
        """Event handler: click on the clear text icon in a text entry."""
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            entry.set_text('')
