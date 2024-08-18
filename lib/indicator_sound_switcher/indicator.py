import os.path
import logging
import time
from importlib.metadata import version

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk, GLib

try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
except ValueError:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as AppIndicator

from .lib_pulseaudio import *
from .card import CardProfile, Card
from .port import Port
from .stream import Source, Sink
from .config import Config, KeyboardManager
from .prefs import PreferencesDialog

# Global definitions
APP_ID      = 'indicator-sound-switcher'
APP_NAME    = 'Sound Switcher Indicator'
APP_LICENCE = """This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License version 3, as published
by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranties of
MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see http://www.gnu.org/licenses/"""

# Determine app version
APP_VERSION = version(APP_ID)

YESNO = {False: 'No', True: 'Yes'}

CARD_NONE_SINK   = -1
CARD_NONE_SOURCE = -2

# Max number of retries to (re)connect to the PulseAudio daemon before giving up
PULSEAUDIO_MAX_RETRIES = 100


# noinspection PyUnusedLocal
class SoundSwitcherIndicator(GObject.GObject):

    def __init__(self):
        """Constructor."""
        GObject.GObject.__init__(self)

        # Create the indicator object
        self.ind = AppIndicator.Indicator.new(
            APP_ID,
            'indicator-sound-switcher-symbolic',
            AppIndicator.IndicatorCategory.HARDWARE)
        self.ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        # Initialise PulseAudio object lists and references
        self.cards          = {}
        self.sources        = {}
        self.source_outputs = {}
        self.sinks          = {}
        self.sink_inputs    = {}
        self._pacb_card_info          = None
        self._pacb_context_notify     = None
        self._pacb_context_subscribe  = None
        self._pacb_context_success    = None
        self._pacb_server_info        = None
        self._pacb_sink_info          = None
        self._pacb_sink_input_info    = None
        self._pacb_source_info        = None
        self._pacb_source_output_info = None
        self.pa_context               = None
        self.pa_context_connected     = False
        self.pa_context_failed        = False
        self.pa_connecting            = False

        # Initialise menu items
        self.item_header_inputs     = None
        self.item_separator_inputs  = None
        self.item_header_outputs    = None
        self.item_separator_outputs = None

        # Load configuration, if any
        self.config_file_name = os.path.join(GLib.get_user_config_dir(), APP_ID + '.json')
        self.config           = self.config_load()
        self.config_devices   = self.config['devices']

        # Initialise the keyboard manager
        self.keyboard_manager = KeyboardManager(self.on_port_keyboard_shortcut)
        self.keyboard_manager.bind_keys(self.config)

        # Create a menu
        self.menu = Gtk.Menu()
        self.ind.set_menu(self.menu)

        # Initialise the PulseAudio interface
        self.pa_mainloop = None
        self.pa_mainloop_api = None

        # Setup PulseAudio callbacks
        self._pacb_card_info          = pa_card_info_cb_t         (self.pacb_card_info)
        self._pacb_context_notify     = pa_context_notify_cb_t    (self.pacb_context_notify)
        self._pacb_context_subscribe  = pa_context_subscribe_cb_t (self.pacb_context_subscribe)
        self._pacb_context_success    = pa_context_success_cb_t   (self.pacb_context_success)
        self._pacb_server_info        = pa_server_info_cb_t       (self.pacb_server_info)
        self._pacb_sink_info          = pa_sink_info_cb_t         (self.pacb_sink_info)
        self._pacb_sink_input_info    = pa_sink_input_info_cb_t   (self.pacb_sink_input_info)
        self._pacb_source_info        = pa_source_info_cb_t       (self.pacb_source_info)
        self._pacb_source_output_info = pa_source_output_info_cb_t(self.pacb_source_output_info)

        # Connect to the daemon, this will also refill the menu
        self.pulseaudio_connect()

    # ------------------------------------------------------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------------------------------------------------------

    def do_context_subscribe(self, facility: int, kind: int, index: int) -> bool:
        """Context status change handler. Always runs on the GUI thread."""
        logging.debug('.do_context_subscribe(facility: %d, kind: %d, index: %d)', facility, kind, index)

        # Dispatch the callback
        # -- Source
        if facility == PA_SUBSCRIPTION_EVENT_SOURCE:
            # Active port change events are fired as PA_SUBSCRIPTION_EVENT_CHANGE
            if kind == PA_SUBSCRIPTION_EVENT_NEW or kind == PA_SUBSCRIPTION_EVENT_CHANGE:
                self.synchronise_op(
                    'pa_context_get_source_info_by_index()',
                    pa_context_get_source_info_by_index(self.pa_context, index, self._pacb_source_info, None))
            elif kind == PA_SUBSCRIPTION_EVENT_REMOVE:
                self.source_remove(index)

        # -- Source output
        elif facility == PA_SUBSCRIPTION_EVENT_SOURCE_OUTPUT:
            if kind == PA_SUBSCRIPTION_EVENT_NEW:
                self.synchronise_op(
                    'pa_context_get_source_output_info()',
                    pa_context_get_source_output_info(self.pa_context, index, self._pacb_source_output_info, None))
            elif kind == PA_SUBSCRIPTION_EVENT_REMOVE:
                self.source_output_remove(index)

        # -- Sink
        elif facility == PA_SUBSCRIPTION_EVENT_SINK:
            # Active port change events are fired as PA_SUBSCRIPTION_EVENT_CHANGE
            if kind == PA_SUBSCRIPTION_EVENT_NEW or kind == PA_SUBSCRIPTION_EVENT_CHANGE:
                self.synchronise_op(
                    'pa_context_get_sink_info_by_index()',
                    pa_context_get_sink_info_by_index(self.pa_context, index, self._pacb_sink_info, None))
            elif kind == PA_SUBSCRIPTION_EVENT_REMOVE:
                self.sink_remove(index)

        # -- Sink input
        elif facility == PA_SUBSCRIPTION_EVENT_SINK_INPUT:
            if kind == PA_SUBSCRIPTION_EVENT_NEW:
                self.synchronise_op(
                    'pa_context_get_sink_input_info()',
                    pa_context_get_sink_input_info(self.pa_context, index, self._pacb_sink_input_info, None))
            elif kind == PA_SUBSCRIPTION_EVENT_REMOVE:
                self.sink_input_remove(index)

        # -- Card
        elif facility == PA_SUBSCRIPTION_EVENT_CARD:
            if kind == PA_SUBSCRIPTION_EVENT_NEW or kind == PA_SUBSCRIPTION_EVENT_CHANGE:
                self.synchronise_op(
                    'pa_context_get_card_info_by_index()',
                    pa_context_get_card_info_by_index(self.pa_context, index, self._pacb_card_info, None))
            elif kind == PA_SUBSCRIPTION_EVENT_REMOVE:
                self.card_remove(index)

        # -- Server
        elif facility == PA_SUBSCRIPTION_EVENT_SERVER:
            if kind == PA_SUBSCRIPTION_EVENT_CHANGE:
                self.synchronise_op(
                    'pa_context_get_server_info()',
                    pa_context_get_server_info(self.pa_context, self._pacb_server_info, None))

        # Prevent this method from being called again
        return False

    @staticmethod
    def on_about(*args):
        """Signal handler: About item clicked."""
        logging.debug('.on_about()')
        dialog = Gtk.AboutDialog()
        dialog.set_program_name(APP_NAME)
        dialog.set_copyright(_('Written by Dmitry Kann'))
        dialog.set_license(APP_LICENCE)
        dialog.set_version(APP_VERSION)
        dialog.set_website('http://yktoo.com')
        dialog.set_website_label('yktoo.com')
        dialog.set_logo_icon_name('indicator-sound-switcher')
        dialog.connect('response', lambda *largs: dialog.destroy())
        dialog.run()

    def on_preferences(self, *args):
        """Signal handler: Preferences item clicked."""
        logging.debug('.on_preferences()')
        PreferencesDialog.show(self)

    def on_quit(self, *args):
        """Signal handler: Quit item clicked."""
        logging.debug('.on_quit()')
        self.shutdown()

    def on_refresh(self, *args):
        """Signal handler: Refresh item clicked."""
        logging.debug('.on_refresh()')
        self.keyboard_manager.bind_keys(self.config)
        self.menu_setup()
        self.update_pa_items()

    def on_select_port(self, widget, data):
        """Signal handler: port selection item clicked."""
        if widget.get_active():
            self.activate_port(*data)

    def on_port_keyboard_shortcut(self, shortcut, data: list):
        """Signal handler: port selected by a keyboard shortcut."""
        logging.debug('.on_port_keyboard_shortcut(`%s`, `%s`)', shortcut, data)

        # Build a list of available devices/ports
        idx_active = -1
        card_ports = []  # List of (card, port) tuples
        for idx in range(len(data)):
            card, port = self.find_card_port_by_name(*data[idx])
            if card and port and (port.is_available or port.always_avail):
                card_ports.append((card, port))

                # Check if there's an active port
                if idx_active < 0 and port.is_active:
                    idx_active = len(card_ports)-1
                    logging.debug(
                        '  * card `%s`, port %s is currently active (index %d)', card.name, port.get_id_text(), idx_active)

        # If there's any port on the list
        if card_ports:
            # If none of the ports is active, or the last is active, start over from 0. Otherwise, pick the next one
            # from the list
            idx_active = 0 if idx_active < 0 or idx_active == len(card_ports)-1 else idx_active+1
            logging.debug('  * switching to index %d amongst %d device ports', idx_active, len(card_ports))

            # Activate the port
            card, port = card_ports[idx_active]
            self.activate_port(card.index, port.name)

    # ------------------------------------------------------------------------------------------------------------------
    # PulseAudio callbacks
    # ------------------------------------------------------------------------------------------------------------------

    def pacb_card_info(self, context, struct, eol, user_data):
        """Card info callback."""
        if struct:
            # New card info arrived
            self.card_info(struct.contents)

        # Wake up PA's thread
        pa_threaded_mainloop_signal(self.pa_mainloop, 0)

    def pacb_context_notify(self, context, user_data):
        """Connection status callback."""
        ctxstate = pa_context_get_state(context)

        # Context connected and ready
        if ctxstate == PA_CONTEXT_READY:
            self.pa_context_connected = True
            logging.info('Context connected')

        # Context connection failed
        elif ctxstate == PA_CONTEXT_FAILED:
            self.pa_context_failed = True
            self.pa_context = None
            logging.warning('Context failed')

            # If we're not connecting, try to reconnect
            if not self.pa_connecting:
                logging.info('Reconnecting to PulseAudio')
                GObject.idle_add(self.pulseaudio_connect)

        # Context connection ended - end the mainloop
        elif ctxstate == PA_CONTEXT_TERMINATED:
            logging.info('Context terminated')

    def pacb_context_subscribe(self, context, event_type, index, user_data):
        """Context subscription callback."""
        facility = event_type & PA_SUBSCRIPTION_EVENT_FACILITY_MASK
        kind     = event_type & PA_SUBSCRIPTION_EVENT_TYPE_MASK

        # Pass the event on to the main GUI thread
        GObject.idle_add(self.do_context_subscribe, facility, kind, index)

        # Wake up PA's thread
        pa_threaded_mainloop_signal(self.pa_mainloop, 0)

    def pacb_context_success(self, context, c_int, user_data):
        """Context success callback."""
        # Wake up PA's thread
        pa_threaded_mainloop_signal(self.pa_mainloop, 0)

    def pacb_server_info(self, context, struct, user_data):
        """Server info callback."""
        if struct:
            self.activate_sink  (struct.contents.default_sink_name.decode())
            self.activate_source(struct.contents.default_source_name.decode())

        # Schedule a port status update on the main GUI thread
        GObject.idle_add(self.card_update_all_ports_activity)

        # Wake up PA's thread
        pa_threaded_mainloop_signal(self.pa_mainloop, 0)

    def pacb_sink_info(self, context, struct, index, user_data):
        """Sink info callback."""
        if struct:
            self.sink_info(struct.contents)

        # Wake up PA's thread
        pa_threaded_mainloop_signal(self.pa_mainloop, 0)

    def pacb_sink_input_info(self, context, struct, eol, user_data):
        """Sink input info callback."""
        if struct:
            # New sink input info arrived
            self.sink_input_add(struct.contents.index, struct.contents.name.decode(), struct.contents.sink)

        # Wake up PA's thread
        pa_threaded_mainloop_signal(self.pa_mainloop, 0)

    def pacb_source_info(self, context, struct, index, user_data):
        """Source info callback."""
        # Skip "sink monitor" sources
        if struct and (struct.contents.monitor_of_sink == PA_INVALID_INDEX):
            self.source_info(struct.contents)

        # Wake up PA's thread
        pa_threaded_mainloop_signal(self.pa_mainloop, 0)

    def pacb_source_output_info(self, context, struct, eol, user_data):
        """Source output info callback."""
        if struct:
            # New source output info arrived
            self.source_output_add(struct.contents.index, struct.contents.name.decode())

        # Wake up PA's thread
        pa_threaded_mainloop_signal(self.pa_mainloop, 0)

    # ------------------------------------------------------------------------------------------------------------------
    # Card list related procs
    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def card_fetch_profiles(num_profiles: int, pa_profiles: list, active_profile_name: str) -> dict:
        """Extract card profiles from a PA data structure.
        :return: profiles as a dictionary {name: CardProfile}
        """
        profiles = {}
        idx = 0
        while idx < num_profiles:
            pa_profile = pa_profiles[idx]
            profile_name = pa_profile.name.decode()
            profiles[profile_name] = CardProfile(
                profile_name,
                pa_profile.description.decode(),
                pa_profile.n_sinks,
                pa_profile.n_sources,
                pa_profile.priority,
                profile_name == active_profile_name)
            idx += 1
        return profiles

    @staticmethod
    def card_fetch_ports(pa_ports: list, ports_cfg: Config) -> dict:
        """Extract card ports from a PA data structure.
        :return: ports as a dictionary {name: Port}
        """
        ports = {}
        if pa_ports:
            idx = 0
            while True:
                port_ptr = pa_ports[idx]
                # NULL pointer terminates the array
                if not port_ptr:
                    break
                pa_port = port_ptr.contents
                port_name = pa_port.name.decode()
                port_cfg = ports_cfg[port_name]
                # Add a port object
                ports[port_name] = Port(
                    port_name,
                    pa_port.description.decode(),
                    port_cfg['name', ''],
                    pa_port.priority,
                    pa_port.available != PA_PORT_AVAILABLE_NO,
                    bool(port_cfg['visible', True]),
                    pa_port.direction,
                    [pa_port.profiles[i].contents.name.decode() for i in range(0, pa_port.n_profiles)],
                    port_cfg['preferred_profile', None],
                    port_cfg['always_available', False])
                idx += 1
        return ports

    def card_create_menu_items(self, card):
        """Insert menu items for the given card."""
        for port in card.ports.values():
            # If the port and its section are to be displayed in the menu
            if port.is_visible:
                hdr_item = self.item_header_outputs    if port.is_output else self.item_header_inputs
                sep_item = self.item_separator_outputs if port.is_output else self.item_separator_inputs
                if hdr_item is not None and sep_item is not None:
                    # Create a menu item and save it in the port object
                    port.menu_item = self.menu_insert_ordered_item(
                        hdr_item, sep_item, port.get_menu_item_title(), port.is_available or port.always_avail)
                    # Bind a click handler
                    port.handler_id = port.menu_item.connect('activate', self.on_select_port, (card.index, port.name))

    def card_info(self, data):
        """Register a new Card instance or updates an existing one."""
        # Fetch properties from the data struct
        index         = data.index
        name          = data.name.decode()
        act_prof_name = data.active_profile.contents.name.decode()

        # Try to fetch the card's configuration
        card_cfg = self.config_devices[name]

        # Prepare ports array
        card_ports = self.card_fetch_ports(data.ports, card_cfg['ports'])

        # If card already exists, fetch it
        if index in self.cards:
            card = self.cards[index]
            logging.debug('  * Card[%d] `%s` updated', index, card.name)

            # Update active profile
            cur_profile = card.get_active_profile()
            for profile in card.profiles.values():
                profile.is_active = profile.name == act_prof_name
                if profile.is_active and profile != cur_profile:
                    logging.debug(
                        '    * Switched active profile: %s ⇒ %s',
                        cur_profile.get_id_text() if cur_profile else 'None',
                        profile.get_id_text())

            # Update port availability
            for new_port in card_ports.values():
                if new_port.name in card.ports:
                    port = card.ports[new_port.name]
                    if port.is_available != new_port.is_available:
                        port.is_available = new_port.is_available
                        logging.debug(
                            '    * Port is made %savailable: %s',
                            '' if port.is_available else 'un', port.get_id_text())

        # Otherwise, register a new card object
        else:
            logging.debug('  + Card[%d] added: `%s`, driver: `%s`', index, name, data.driver.decode())

            # Prepare profiles dict
            card_profiles = self.card_fetch_profiles(data.n_profiles, data.profiles, act_prof_name)
            # Log profiles
            for profile in card_profiles.values():
                logging.debug(
                    '    + Card profile added: %s, %d sinks, %d sources, priority: %d%s',
                    profile.get_id_text(), profile.num_sinks, profile.num_sources, profile.priority,
                    ' -- Active' if profile.is_active else '')
            # Log ports
            for port in card_ports.values():
                logging.debug(
                    '    + Card port added: %s; priority: %d; direction: %d; available: %s',
                    port.get_id_text(), port.priority, port.direction, YESNO[port.is_available])
                if port.profiles:
                    for port_profile_name in port.profiles:
                        logging.debug('      . Supported profile: `%s`', port_profile_name)

            # If there's no port on this card (most likely Bluetooth), create a couple of dummy ones
            if not card_ports:
                card_ports['#dummy_out'] = Port(
                    '#dummy_out', None, '', -1, True, True, PA_DIRECTION_OUTPUT, None, None, False)
                card_ports['#dummy_in']  = Port(
                    '#dummy_in',  None, '', -1, True, True, PA_DIRECTION_INPUT,  None, None, False)

            # Create and register a new card object
            self.cards[index] = card = Card(
                index, name, card_cfg['name', ''], data.driver.decode(), card_profiles, card_ports,
                data.proplist.contents)

            # Add a menu item for each card port
            self.card_create_menu_items(card)

    def card_remove(self, index: int):
        """Remove a Card instance by its index (PulseAudio's card index)."""
        if index in self.cards:
            card = self.cards[index]
            logging.debug('  - Card[%d] removed: `%s`', index, card.name)

            # Remove all card ports' menu items
            for port in card.ports.values():
                if port.menu_item:
                    self.menu.remove(port.menu_item)

            # Remove the card object
            del self.cards[index]

    def card_remove_all(self):
        """Remove all Card instances."""
        for index in list(self.cards.keys()):
            self.card_remove(index)

    def card_update_all_ports_activity(self):
        """Update the is_active state for ports on all cards."""
        for card in self.cards.values():
            card.update_port_activity(self.sources, self.sinks)

    def card_switch_profile(self, port, can_keep_current: bool) -> bool:
        """Find the most appropriate profile for the given card port and activate it on its card.
        :param port: Port that we need the best profile for
        :param can_keep_current: whether the currently active profile is compatible with this port, so we can keep it
        :return whether profile has been switched
        """
        card = port.owner_card

        # Compile a list of profiles supporting the port
        profiles = {pname: card.profiles[pname] for pname in port.profiles if pname in card.profiles}
        if not profiles:
            logging.warning(
                '! Card[%d] has no supported profiles for port `%s`, supposedly device misconfiguration',
                card.index, port.name)
            return False

        # If the port is given a preferred profile, verify it's valid for this port
        selected_profile = None
        if port.pref_profile:
            if port.pref_profile in profiles:
                selected_profile = profiles[port.pref_profile]
                logging.debug('* Preferred profile `%s` is specified for port %s', port.pref_profile, port.get_id_text())
            else:
                logging.warning(
                    '! Cannot activate preferred profile `%s` for port %s as this port doesn\'t support it',
                    port.pref_profile, port.get_id_text())

        # If no preferred profile given and the current one is fine, do nothing
        if not selected_profile and can_keep_current:
            return False

        # Otherwise, pick the one with max priority
        if not selected_profile:
            selected_profile = max(profiles.values(), key=lambda k: k.priority)

        # Don't bother if the profile is already active (it won't help anyway)
        if selected_profile.is_active:
            logging.debug('* Profile %s is already active on card[%d]', selected_profile.get_id_text(), card.index)
            return False

        # Switch the profile
        logging.debug(
            '* Switching card[%d] to profile %s with priority %d',
            card.index, selected_profile.get_id_text(), selected_profile.priority)
        self.synchronise_op(
            'pa_context_set_card_profile_by_index()',
            pa_context_set_card_profile_by_index(
                self.pa_context,
                card.index,
                selected_profile.name.encode(),
                self._pacb_context_success,
                None))

        # Reload all PA objects, except cards, because switching a profile may result in a change in the list of
        # available sources and/or sinks for that card
        self.update_pa_items(update_cards=False)
        return True

    # ------------------------------------------------------------------------------------------------------------------
    # Sink list related procs
    # ------------------------------------------------------------------------------------------------------------------

    def sink_info(self, data):
        """Register a new Sink instance or update an existing one."""
        # Fetch properties from the data struct
        index       = data.index
        name        = data.name.decode()
        description = data.description.decode()

        # If sink already exists, fetch it
        if index in self.sinks:
            logging.debug('  * Sink[%d] updated: `%s`, card %d', index, name, data.card)
            sink = self.sinks[index]

        # Otherwise register a new sink object
        else:
            logging.debug('  + Sink[%d] added: `%s`, card %d', index, name, data.card)

            # Prepare ports array
            sink_ports = {}
            sink_name = ''
            sink_visible = False

            # If it's a virtual sink, add a dummy port
            virtual_card = self.is_virtual_card(data.card)
            if virtual_card:
                port = Port('#dummy_out', None, '', -1, True, True, PA_DIRECTION_OUTPUT, None, None, False)
                sink_ports[port.name] = port
                sink_cfg = self.config_devices['virtual']['sinks'][name]
                sink_name    = sink_cfg['name', '']
                sink_visible = bool(sink_cfg['visible', True])

            # Else iterate through ports[] (array of pointers to structs)
            elif data.ports:
                idx_port = 0
                while True:
                    port_ptr = data.ports[idx_port]
                    # NULL pointer terminates the array
                    if not port_ptr:
                        break

                    port_struct = port_ptr.contents
                    port = Port(
                        port_struct.name.decode(),
                        port_struct.description.decode(),
                        '',
                        port_struct.priority,
                        port_struct.available != PA_PORT_AVAILABLE_NO,
                        False,
                        PA_DIRECTION_OUTPUT,
                        None,
                        None,
                        False)
                    sink_ports[port.name] = port
                    logging.debug(
                        '    + Sink port added: %s; priority: %d; available: %s',
                        port.get_id_text(), port.priority, YESNO[port.is_available])
                    idx_port += 1

            # Create and register a new instance of Sink object (this will also set owner_stream in each port)
            sink = Sink(index, name, sink_name, description, sink_ports, data.card)
            self.sinks[index] = sink

            # If it's a virtual sink, and it's visible, create its menu item
            if virtual_card and sink_visible and self.item_header_outputs is not None and \
                    self.item_separator_outputs is not None:
                for port in sink_ports.values():
                    port.menu_item = self.menu_insert_ordered_item(
                        self.item_header_outputs,
                        self.item_separator_outputs,
                        port.get_menu_item_title(),
                        port.is_available or port.always_avail)
                    # Bind a click handler
                    port.handler_id = port.menu_item.connect(
                        'activate', self.on_select_port, (CARD_NONE_SINK, index))

        # Update sink's active port, if there's any
        if data.active_port:
            port_name = data.active_port.contents.name.decode()
            logging.debug('    * Activated sink port `%s`', port_name)
            sink.activate_port_by_name(port_name)

            # Update all card ports
            self.card_update_all_ports_activity()

    def sink_remove(self, index: int):
        """Remove a Sink instance by its index (PulseAudio's sink index)."""
        if index in self.sinks:
            sink = self.sinks[index]
            logging.debug('  - Sink[%d] removed: `%s`', index, sink.name)

            # Remove all sink ports' menu items
            for port in sink.ports.values():
                if port.menu_item:
                    self.menu.remove(port.menu_item)

            # Also remove the sink object from sinks[]
            del self.sinks[index]

    def sink_remove_all(self):
        """Remove all Sink instances."""
        for index in list(self.sinks.keys()):
            self.sink_remove(index)

    # ------------------------------------------------------------------------------------------------------------------
    # Sink input list related procs
    # ------------------------------------------------------------------------------------------------------------------

    def sink_input_add(self, index: int, name: str, sink: int):
        """Register a new SinkInput instance or update an existing one."""
        # Remove existing sink input with the same index, if any
        self.sink_input_remove(index)
        logging.debug('  + Sink input[%d] added: `%s` -> sink %d', index, name, sink)

        # Register the new sink input
        self.sink_inputs[index] = name

    def sink_input_remove(self, index: int):
        """Remove a SinkInput instance by its index (PulseAudio's sink input index)."""
        if index in self.sink_inputs:
            logging.debug('  - Sink input[%d] removed: `%s`', index, self.sink_inputs[index])

            # Remove the sink input
            del self.sink_inputs[index]

    def sink_input_remove_all(self):
        """Remove all SinkInput instances."""
        for index in list(self.sink_inputs.keys()):
            self.sink_input_remove(index)

    # ------------------------------------------------------------------------------------------------------------------
    # Source list related procs
    # ------------------------------------------------------------------------------------------------------------------

    def source_info(self, data):
        """Register a new Source instance or update an existing one."""
        # Fetch properties from the data struct
        index       = data.index
        name        = data.name.decode()
        description = data.description.decode()

        # If source already exists, fetch it
        if index in self.sources:
            logging.debug('  * Source[%d] updated: `%s`, card %d', index, name, data.card)
            source = self.sources[index]

        # Otherwise, register a new source object
        else:
            logging.debug('  + Source[%d] added: `%s`, card %d', index, name, data.card)

            # Prepare ports array
            source_ports = {}
            source_name = ''
            source_visible = False

            # If it's a virtual sink, add a dummy port
            virtual_card = self.is_virtual_card(data.card)
            if virtual_card:
                port = Port('#dummy_in', None, '', -1, True, True, PA_DIRECTION_INPUT, None, None, False)
                source_ports[port.name] = port
                source_cfg = self.config_devices['virtual']['sources'][name]
                source_name    = source_cfg['name', '']
                source_visible = bool(source_cfg['visible', True])

            # Else iterate through ports[] (array of pointers to structs)
            elif data.ports:
                idx_port = 0
                while True:
                    port_ptr = data.ports[idx_port]
                    # NULL pointer terminates the array
                    if not port_ptr:
                        break

                    port_struct = port_ptr.contents
                    port = Port(
                        port_struct.name.decode(),
                        port_struct.description.decode(),
                        '',
                        port_struct.priority,
                        port_struct.available != PA_PORT_AVAILABLE_NO,
                        False,
                        PA_DIRECTION_INPUT,
                        None,
                        None,
                        False)
                    source_ports[port.name] = port
                    logging.debug(
                        '    + Source port added: %s; priority: %d; available: %s',
                        port.get_id_text(), port.priority, YESNO[port.is_available])
                    idx_port += 1

            # Create and register a new instance of Source object (this will also set owner_stream in each port)
            source = Source(index, name, source_name, description, source_ports, data.card)
            self.sources[index] = source

            # If it's a virtual source, create its menu item
            if virtual_card and source_visible and self.item_header_inputs is not None and \
                    self.item_separator_inputs is not None:
                for port in source_ports.values():
                    port.menu_item = self.menu_insert_ordered_item(
                        self.item_header_inputs,
                        self.item_separator_inputs,
                        port.get_menu_item_title(),
                        port.is_available or port.always_avail)
                    # Bind a click handler
                    port.handler_id = port.menu_item.connect(
                        'activate', self.on_select_port, (CARD_NONE_SOURCE, index))

        # Update source's active port, if there's any
        if data.active_port:
            port_name = data.active_port.contents.name.decode()
            logging.debug('    * Activated source port `%s`', port_name)
            source.activate_port_by_name(port_name)

            # Update all card ports
            self.card_update_all_ports_activity()

    def source_remove(self, index: int):
        """Remove a Source instance by its index (PulseAudio's source index)."""
        if index in self.sources:
            source = self.sources[index]
            logging.debug('  - Source[%d] removed: `%s`', index, source.name)

            # Remove all source ports' menu items
            for port in source.ports.values():
                if port.menu_item:
                    self.menu.remove(port.menu_item)

            # Also remove the source object from sources[]
            del self.sources[index]

    def source_remove_all(self):
        """Remove all Source instances."""
        for index in list(self.sources.keys()):
            self.source_remove(index)

    # ------------------------------------------------------------------------------------------------------------------
    # Source output list related procs
    # ------------------------------------------------------------------------------------------------------------------

    def source_output_add(self, index: int, name: str):
        """Register a new SourceOutput instance or update an existing one."""
        # Remove existing source output with the same index, if any
        self.source_output_remove(index)
        logging.debug('  + Source output[%d] added: `%s`', index, name)

        # Register the new source output
        self.source_outputs[index] = name

    def source_output_remove(self, index: int):
        """Remove a SourceOutput instance by its index (PulseAudio's source output index)."""
        if index in self.source_outputs:
            logging.debug('  - Source output[%d] removed: `%s`', index, self.source_outputs[index])

            # Remove the source output
            del self.source_outputs[index]

    def source_output_remove_all(self):
        """Remove all SourceOutput instances."""
        for index in list(self.source_outputs.keys()):
            self.source_output_remove(index)

    # ------------------------------------------------------------------------------------------------------------------
    # Other methods
    # ------------------------------------------------------------------------------------------------------------------

    def config_load(self) -> Config:
        """Read the configuration from the corresponding file."""
        return Config.load_from_file(self.config_file_name)

    def config_save(self):
        """Write the configuration out to the corresponding file."""
        self.config.save_to_file(self.config_file_name)

    def activate_port(self, idx_card: int, stream_or_port):
        """Switch input or output to the given port or virtual stream.
        :param idx_card:       device index in the cards[] list
        :param stream_or_port: either stream index if idx_card refers to a dummy sink/source, or name of the port on the
                               card given by idx_card
        """
        logging.debug('.activate_port(%d, %s)', idx_card, stream_or_port)

        # If it's a dummy (virtual) card sink, buf[1] is the sink's index
        if idx_card == CARD_NONE_SINK:
            port       = None
            idx_stream = stream_or_port
            stream     = self.sinks[idx_stream]
            is_output  = True
            logging.info('# Virtual sink[%d] `%s` selected', idx_stream, stream.name)

        # If it's a dummy (virtual) card source, buf[1] is the source's index
        elif idx_card == CARD_NONE_SOURCE:
            port       = None
            idx_stream = stream_or_port
            stream     = self.sources[idx_stream]
            is_output  = False
            logging.info('# Virtual source[%d] `%s` selected', idx_stream, stream.name)

        # Otherwise, it's a real device and buf[1] is the port's name
        else:
            port_name = stream_or_port

            # Find the card and validate its port
            card = self.cards[idx_card]
            if port_name not in card.ports:
                logging.warning('# Failed to find port `%s` on card `%s`', port_name, card.name)
                return

            port = card.ports[port_name]
            is_output = port.is_output
            logging.info('# Card[%d], port %s selected', idx_card, port.get_id_text())

            # Try to find a matching stream
            stream = card.find_stream_port(port, self.sources, self.sinks)[0]

            # Switch profile if necessary
            if self.card_switch_profile(port, stream is not None):
                # Profile is changed: retry searching for the stream
                stream = card.find_stream_port(port, self.sources, self.sinks)[0]

            # If no stream found, that's an error
            if stream is None:
                logging.error('Failed to map card[%d], port `%s` to a stream', idx_card, port_name)
                return

        # Switching output
        if is_output:
            # Change the default sink
            self.synchronise_op(
                'pa_context_set_default_sink()',
                pa_context_set_default_sink(self.pa_context, stream.name.encode(), self._pacb_context_success, None)
            )

            # Change the active port, if it's not a dummy one
            if port is not None and not port.is_dummy:
                pa_context_set_sink_port_by_index(
                    self.pa_context, stream.index, port.name.encode(), self._pacb_context_success, None)

            # Move all active sink inputs to the selected sink
            for idx in self.sink_inputs.keys():
                self.synchronise_op(
                    'pa_context_move_sink_input_by_index()',
                    pa_context_move_sink_input_by_index(
                        self.pa_context, idx, stream.index, self._pacb_context_success, None))

        # Switching input
        else:
            # Change the default source
            self.synchronise_op(
                'pa_context_set_default_source()',
                pa_context_set_default_source(
                    self.pa_context, stream.name.encode(), self._pacb_context_success, None))

            # Change the active port, if it's not a dummy one
            if port is not None and not port.is_dummy:
                self.synchronise_op(
                    'pa_context_set_source_port_by_index()',
                    pa_context_set_source_port_by_index(
                        self.pa_context, stream.index, port.name.encode(), self._pacb_context_success, None))

            # Move all active source outputs to the selected source
            for idx in self.source_outputs.keys():
                self.synchronise_op(
                    'pa_context_move_source_output_by_index()',
                    pa_context_move_source_output_by_index(
                        self.pa_context, idx, stream.index, self._pacb_context_success, None))

    def activate_sink(self, name: str):
        """Activate a sink by its name."""
        logging.debug('* Activated sink: `%s`', name)
        for sink in self.sinks.values():
            sink.is_active = sink.name == name

    def activate_source(self, name: str):
        """Activate a source by its name."""
        logging.debug('* Activated source: `%s`', name)
        for source in self.sources.values():
            source.is_active = source.name == name

    def find_card_port_by_name(self, card_name: str, port_name: str) -> tuple:
        """Find a card and its port by their names, and return both as a tuple. If the card is found and the port isn't,
        return (card, None); if neither is found, return (None, None)."""
        # Iterate known cards
        for idx, card in self.cards.items():
            if card.name == card_name:
                # If the port isn't found for the card, return only the card
                if port_name not in card.ports:
                    logging.warning('# Failed to find port `%` on card `%s`', port_name, card_name)
                    return card, None

                # Return the card and the port
                return card, card.ports[port_name]

        # Card not found
        logging.warning('Failed to find card `%s` among the available devices', card_name)
        return None, None

    @staticmethod
    def run():
        """Run the application."""
        # Run the main event loop
        Gtk.main()

    def menu_append_item(self, label: str = None, activate_signal: callable = None):
        """Add a menu or separator item to the indicator menu.
        :param label: text label for the item. If None, a separator menu item is created.
        :param activate_signal: activate signal handler. If None,  the item will be greyed out.
        :return: the created item
        """
        if label is None:
            logging.debug('.menu_append_item(): appending separator')
            item = Gtk.SeparatorMenuItem()
        else:
            logging.debug('.menu_append_item(): appending item `%s`', label)
            item = Gtk.MenuItem.new_with_mnemonic(label)
            if activate_signal is not None:
                item.connect("activate", activate_signal, None)
            else:
                item.set_sensitive(False)
        item.show()
        self.menu.append(item)
        return item

    def menu_insert_ordered_item(self, after_item, before_item, label: str, show: bool):
        """Insert a new menu item into the indicator menu while maintaining the alphabetical order of the items.
        :param after_item: the item to insert after, or None if unbounded
        :param before_item: the item to insert before, or None if unbounded
        :param label: text label for the item
        :param show: whether to make the newly inserted item visible
        :return: the created item
        """
        # Indent the label a little
        label = "    " + label

        # Find out item indexes
        items = self.menu.get_children()
        idx_from = 0 if after_item is None else items.index(after_item) + 1
        idx_to   = items.index(before_item)

        # If there's at least one item, get the group from it
        group = [] if idx_to == idx_from else items[idx_from].get_group()

        # Create and set up a new radio item
        new_item = Gtk.RadioMenuItem.new_with_mnemonic(group, label)
        if show:
            new_item.show()

        # Find an appropriate position for the item so that they are in alphabetical order
        i = idx_from
        while (i < idx_to) and (label >= items[i].get_label()):
            i += 1

        # Insert the item
        logging.debug(
            '.menu_insert_ordered_item(): inserting item `%s` at index %d%s',
            label, i, ' (hidden)' if not show else '')
        self.menu.insert(new_item, i)
        return new_item

    def menu_setup(self):
        """Initialise the indicator menu."""
        # Remove all menu items
        for item in self.menu.get_children():
            self.menu.remove(item)

        # Make the input list section, if needed
        if bool(self.config['show_inputs', True]):
            self.item_header_inputs = self.menu_append_item(_('Inputs'))
            self.item_separator_inputs = self.menu_append_item()
        else:
            self.item_header_inputs = None
            self.item_separator_inputs = None

        # Make the output list section, if needed
        if bool(self.config['show_outputs', True]):
            self.item_header_outputs = self.menu_append_item(_('Outputs'))
            self.item_separator_outputs = self.menu_append_item()
        else:
            self.item_header_outputs = None
            self.item_separator_outputs = None

        # Add static items
        self.menu_append_item(_('_Refresh'),      self.on_refresh)
        self.menu_append_item(_('_Preferences…'), self.on_preferences)
        self.menu_append_item(_('_About'),        self.on_about)
        self.menu_append_item(_('_Quit'),         self.on_quit)

    def pulseaudio_connect(self):
        """Try to connect to the PulseAudio daemon up to PULSEAUDIO_MAX_RETRIES times. Exit the app if failed."""
        self.pa_connecting = True
        try:
            # Cleanup and refill the menu with 'static' items
            self.menu_setup()

            # Loop until we have a connection
            attempt = 1
            succeeded = False
            while attempt <= PULSEAUDIO_MAX_RETRIES:
                # Try to establish a connection
                logging.debug('Trying to connect to PulseAudio daemon, attempt #%d', attempt)
                succeeded = self.pulseaudio_initialise()
                if succeeded:
                    break
                # Sleep 2 seconds on a failure
                time.sleep(2)
                attempt += 1

            # If connection succeeded
            if succeeded:
                # Update PulseAudio environment info
                self.update_pa_items()

                # Subscribe to context-specific daemon state changes
                self.synchronise_op(
                    'pa_context_subscribe()',
                    pa_context_subscribe(
                        self.pa_context,
                        PA_SUBSCRIPTION_MASK_CARD       |
                        PA_SUBSCRIPTION_MASK_SINK       |
                        PA_SUBSCRIPTION_MASK_SINK_INPUT |
                        PA_SUBSCRIPTION_MASK_SERVER     |
                        PA_SUBSCRIPTION_MASK_SOURCE     |
                        PA_SUBSCRIPTION_MASK_SOURCE_OUTPUT,
                        self._pacb_context_success,
                        None))
                pa_context_set_subscribe_callback(self.pa_context, self._pacb_context_subscribe, None)

            # Cleanup otherwise
            else:
                logging.critical('Failed to connect to PulseAudio, exiting')
                self.pulseaudio_shutdown()

        finally:
            self.pa_connecting = False

        # Exit the app if there's no connection
        if not succeeded:
            exit(10)

    def pulseaudio_initialise(self):
        """Initialise PulseAudio context and related objects.
        :return: True if succeeded
        """
        # Create PulseAudio's main loop
        self.pa_mainloop = pa_threaded_mainloop_new()
        self.pa_mainloop_api = pa_threaded_mainloop_get_api(self.pa_mainloop)

        # Create and connect PulseAudio context
        self.pa_context = pa_context_new(self.pa_mainloop_api, APP_NAME.encode())
        self.pa_context_connected = False
        self.pa_context_failed    = False
        pa_context_set_state_callback(self.pa_context, self._pacb_context_notify, None)
        pa_context_connect(self.pa_context, None, 0, None)

        # Start the main loop
        pa_threaded_mainloop_start(self.pa_mainloop)

        # Wait until the context is connected or failed, up to 2 seconds
        cnt = 0
        while cnt < 20 and not (self.pa_context_connected or self.pa_context_failed):
            # Prevent CPU maxout
            time.sleep(0.1)
            cnt += 1

        return self.pa_context_connected

    def pulseaudio_shutdown(self):
        """Clean up PulseAudio context and related objects."""
        # Disconnect and free the context
        if self.pa_context_connected:
            pa_context_disconnect(self.pa_context)
            self.pa_context_connected = False
        if self.pa_context is not None:
            pa_context_unref(self.pa_context)
            self.pa_context = None

        # Stop main loop thread
        if self.pa_mainloop is not None:
            pa_threaded_mainloop_stop(self.pa_mainloop)
            pa_threaded_mainloop_free(self.pa_mainloop)
            self.pa_mainloop = None

    def shutdown(self):
        """Shut down the application."""
        # Close the Preferences dialog if it's open
        PreferencesDialog.quit()

        # Shutdown PulseAudio
        self.pulseaudio_shutdown()

        # Shutdown the keyboard manager
        if self.keyboard_manager:
            self.keyboard_manager.shutdown()

        # Quit
        Gtk.main_quit()

    def synchronise_op(self, name: str, operation):
        """Turn an asynchronous PulseAudio operation into a synchronous one by waiting on the operation to complete.
        Finally, dereference the operation object.
        :param name: operation name for logging purposes
        :param operation: PulseAudio operation to execute
        """
        # Check that there's a successful operation passed
        if not operation:
            logging.error('PulseAudio operation failed: `%s`', name)

        # Lock the main loop. According to the official PA documentation this ought to happen before the operation is
        # created, but since we only have one worker thread (Gtk thread), no race for PA mainloop is expected and this
        # should do
        pa_threaded_mainloop_lock(self.pa_mainloop)

        # Wait on the operation
        while pa_operation_get_state(operation) == PA_OPERATION_RUNNING:
            pa_threaded_mainloop_wait(self.pa_mainloop)

        # Free the operation object
        pa_operation_unref(operation)

        # Unlock the main loop
        pa_threaded_mainloop_unlock(self.pa_mainloop)

    def update_pa_items(self, update_cards=True, update_sources=True, update_sinks=True, update_server=True):
        """Synchronously update information about PulseAudio items: cards, sinks, sources, server etc."""
        logging.debug('.update_pa_items(%s, %s, %s, %s)', update_cards, update_sources, update_sinks, update_server)

        # Remove all PA objects
        if update_cards:
            self.card_remove_all()
        if update_sources:
            self.source_remove_all()
            self.source_output_remove_all()
        if update_sinks:
            self.sink_remove_all()
            self.sink_input_remove_all()

        # Cards
        if update_cards:
            self.synchronise_op(
                'pa_context_get_card_info_list()',
                pa_context_get_card_info_list(self.pa_context, self._pacb_card_info, None))

        if update_sources:
            # Sources
            self.synchronise_op(
                'pa_context_get_source_info_list()',
                pa_context_get_source_info_list(self.pa_context, self._pacb_source_info, None))
            # Source outputs
            self.synchronise_op(
                'pa_context_get_source_output_info_list()',
                pa_context_get_source_output_info_list(self.pa_context, self._pacb_source_output_info, None))

        if update_sinks:
            # Sinks
            self.synchronise_op(
                'pa_context_get_sink_info_list()',
                pa_context_get_sink_info_list(self.pa_context, self._pacb_sink_info, None))
            # Sink inputs
            self.synchronise_op(
                'pa_context_get_sink_input_info_list()',
                pa_context_get_sink_input_info_list(self.pa_context, self._pacb_sink_input_info, None))

        if update_server:
            # Server info
            self.synchronise_op(
                'pa_context_get_server_info()',
                pa_context_get_server_info(self.pa_context, self._pacb_server_info, None))

    @staticmethod
    def is_virtual_card(card_index: int) -> bool:
        """Determine whether a card is a virtual (network or combined input/output) card.
        :param card_index: card index to inspect
        :return: True if the given index corresponds to a virtual card
        """
        # Assume all indexes bigger than 2e9 are virtual cards
        return card_index > 2000000000
