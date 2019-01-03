import logging
import os
from threading import Timer

from gi.repository import Gtk, Pango, GLib

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

        # Create a text renderer for preferred profiles to support ellipsizing the text
        renderer_text = Gtk.CellRendererText()
        renderer_text.props.ellipsize = Pango.EllipsizeMode.END
        self.cb_port_pref_profile.pack_start(renderer_text, True)
        self.cb_port_pref_profile.add_attribute(renderer_text, 'text', 1)

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

    def indicator_refresh_cb(self):
        """Delayed indicator refresh and the configuration write-out callback."""
        if self.refresh_timer:
            # Kill the existing timer, if any
            self.refresh_timer.cancel()
            self.refresh_timer = None

            # Save the configuration
            self.indicator.config_save()

            # Refresh the indicator (on idle)
            GLib.idle_add(self.indicator.on_refresh)

    def schedule_refresh(self):
        """(Re)schedule a delayed indicator refresh and the configuration write-out."""
        # Kill the existing timer, if any
        if self.refresh_timer:
            self.refresh_timer.cancel()

        # Schedule a refresh after 2 seconds
        self.refresh_timer = Timer(2.0, self.indicator_refresh_cb)
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
                    'description':  p.description,
                    'is_output':    p.is_output,
                    'is_available': p.is_available,
                    'profiles':     p.profiles,
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
            port_row.destroy()

        # If there's a selected row
        if row is not None:
            device_cfg = self.get_current_device_config()
            self.e_device_name.set_text(device_cfg['name', ''])

            # Iterate through device's ports
            for name, port in row.device_ports.items():
                # Add a grid
                grid = Gtk.Grid(border_width=12, column_spacing=6, row_spacing=6, hexpand=True)

                # Add a list box row
                port_row = Gtk.ListBoxRow(child=grid)
                port_row.port_name = name
                port_row.port_profiles = port['profiles']

                # Add an icon: checkmark or a cross, depending on the port's current availability
                grid.attach(
                    Gtk.Image.new_from_icon_name('gtk-ok' if port['is_available'] else 'gtk-no', Gtk.IconSize.MENU),
                    0, 0, 1, 2)

                # Add a port title label
                grid.attach(
                    utils.lbl_bold(
                        '{}: {}'.format(_('Out') if port['is_output'] else _('In'), port['description']),
                        xalign=0),
                    1, 0, 1, 1)

                # Add a port name label
                grid.attach(Gtk.Label(name, xalign=0), 1, 1,  1, 1)

                # Add the row to the list box
                self.lbx_ports.add(port_row)

            # Show all rows' widgets
            self.lbx_ports.show_all()

        # Enable widgets
        self.bx_dev_props.set_sensitive(row is not None)

        # Unlock signal handlers
        self.updating_widgets -= 1

    def update_port_props_widgets(self):
        """Update port properties widgets."""
        # Lock signal handlers
        self.updating_widgets += 1

        # Get selected port's config
        device_row = self.lbx_devices.get_selected_row()
        port_row   = self.lbx_ports.get_selected_row()
        port_cfg   = self.get_current_port_config()
        if device_row is not None and port_row is not None and port_cfg is not None:
            self.sw_port_visible.set_active(bool(port_cfg['visible', True]))
            self.sw_port_always_avail.set_active(bool(port_cfg['always_available', False]))
            self.e_port_name.set_text(port_cfg['name', ''] or '')

            # Update port's preferred profile combobox
            self.pref_profile_store.clear()
            self.pref_profile_store.append(['', _('(none)')])
            for name, desc in device_row.device_profiles.items():
                # Only add profiles that the port supports
                if name in port_row.port_profiles:
                    self.pref_profile_store.append([name, desc])
            self.cb_port_pref_profile.set_active_id(port_cfg['preferred_profile', ''] or '')

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

    def get_current_device_config(self) -> Config:
        """Fetch and return the Config object that corresponds to the currently selected device.
        :return: device Config instance or None if there's no device selected.
        """
        row = self.lbx_devices.get_selected_row()
        return self.indicator.config['devices'][row.device_name] if row is not None else None

    def get_current_port_config(self) -> Config:
        """Fetch and return the Config object that corresponds to the currently selected device port. Enforces that it's
        a Config object (not str or False).
        :return: port Config instance or None if there's no port selected.
        """
        device_cfg = self.get_current_device_config()
        port_cfg = None
        if device_cfg is not None:
            row = self.lbx_ports.get_selected_row()
            if row is not None:
                # Make sure the port's config is a Config instance (previously it could also be a string or False)
                port_cfg = device_cfg['ports'][row.port_name]
                if type(port_cfg) is not Config:
                    port_cfg = {}
                    device_cfg['ports'][row.port_name] = port_cfg
        return port_cfg

    def on_destroy(self, dlg):
        """Signal handler: dialog destroying."""
        logging.debug('PreferencesDialog.on_destroy()')
        # Make sure config update has run
        self.indicator_refresh_cb()

    def on_refresh(self, *args):
        """Signal handler: Refresh button clicked."""
        logging.debug('PreferencesDialog.on_refresh()')
        self.update_widgets()

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
            cfg['name'] = val or None
            self.schedule_refresh()

    def on_port_visible_switched(self, widget, data):
        """Signal handler: Port visible switch changed."""
        if self.updating_widgets > 0:
            return
        val = widget.get_active()
        logging.debug('PreferencesDialog.on_port_visible_switched(%s)', val)
        cfg = self.get_current_port_config()
        if cfg is not None:
            cfg['visible'] = None if val else False
            self.enable_port_props_widgets()
            self.schedule_refresh()

    def on_port_always_avail_switched(self, widget, data):
        """Signal handler: Port always available switch changed."""
        if self.updating_widgets > 0:
            return
        val = widget.get_active()
        logging.debug('PreferencesDialog.on_port_always_avail_switched(%s)', val)
        cfg = self.get_current_port_config()
        if cfg is not None:
            cfg['always_available'] = val or None
            self.schedule_refresh()

    def on_port_name_changed(self, entry: Gtk.Entry):
        """Signal handler: Port name entry text changed."""
        if self.updating_widgets > 0:
            return
        val = entry.get_text()
        logging.debug('PreferencesDialog.on_port_name_changed(`%s`)', val)
        cfg = self.get_current_port_config()
        if cfg is not None:
            cfg['name'] = val or None
            self.schedule_refresh()

    def on_port_pref_profile_changed(self, cbox: Gtk.ComboBox):
        """Signal handler: Port preferred profile combobox selection changed."""
        if self.updating_widgets > 0:
            return
        val = cbox.get_active_id()
        logging.debug('PreferencesDialog.on_port_pref_profile_changed(`%s`)', val)
        cfg = self.get_current_port_config()
        if cfg is not None:
            cfg['preferred_profile'] = val or None
            self.schedule_refresh()

    @staticmethod
    def on_entry_clear_click(entry, icon_pos, event):
        """Event handler: click on the clear text icon in a text entry."""
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            entry.set_text('')
