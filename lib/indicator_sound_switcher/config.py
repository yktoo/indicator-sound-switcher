"""
Configuration backend implementation.
"""
import logging
import os
import os.path
import json
import uuid
import gi

from gi.repository import Gdk, Gio, GLib, Gtk

# Keybinder is optional: it only works on X11, and the XDG portal is used on Wayland instead
try:
    gi.require_version('Keybinder', '3.0')
    from gi.repository import Keybinder
except (ImportError, ValueError):
    Keybinder = None

# XDG Desktop Portal definitions
PORTAL_BUS_NAME       = 'org.freedesktop.portal.Desktop'
PORTAL_OBJECT_PATH    = '/org/freedesktop/portal/desktop'
PORTAL_IFACE_SHORTCUT = 'org.freedesktop.portal.GlobalShortcuts'
PORTAL_IFACE_REQUEST  = 'org.freedesktop.portal.Request'
PORTAL_IFACE_SESSION  = 'org.freedesktop.portal.Session'
PORTAL_IFACE_REGISTRY = 'org.freedesktop.host.portal.Registry'


def register_portal_app_id(app_id: str):
    """Tell the XDG portal the app ID of this (unsandboxed) process, which otherwise is guessed from the process'
    systemd scope and can end up being the launching terminal or IDE. Must be called before any other portal interaction
    on the session bus connection. Failures are harmless: sandboxed processes (e.g. snaps) have their app ID determined
    by the sandbox, and portals older than 1.19 have no registry at all.
    :param app_id: app ID, which must match the name of the application's .desktop file
    """
    try:
        Gio.bus_get_sync(Gio.BusType.SESSION, None).call_sync(
            PORTAL_BUS_NAME,
            PORTAL_OBJECT_PATH,
            PORTAL_IFACE_REGISTRY,
            'Register',
            GLib.Variant('(sa{sv})', (app_id, {})),
            None,
            Gio.DBusCallFlags.NONE,
            2000,
            None)
        logging.debug('Registered app ID %s with the XDG portal', app_id)
    except GLib.Error as e:
        logging.debug('Failed to register app ID %s with the XDG portal: %s', app_id, e.message)


class Config(dict):
    """Extension of the standard dict class that overrides item getter to add default value support and sub-dictionary
    autocreation.
    """

    @staticmethod
    def load_from_file(file_name: str):
        """Load, parse and return JSON configuration from a file specified by name.
        :param file_name: Name of the JSON configuration file.
        :returns An instance of Config (empty if the file doesn't exist).
        """
        # Check if the file exists
        if not os.path.isfile(file_name):
            logging.info('Configuration file %s not found, falling back to defaults', file_name)
            return Config()

        # Open and read in the file
        with open(file_name, 'r') as cf:
            # Create instances of Config instead of dict
            conf = json.load(cf, object_hook=lambda dct: Config(dct))
        logging.info('Loaded configuration file %s', file_name)
        return conf

    def save_to_file(self, file_name: str):
        """Save configuration to the given JSON file.
        :param file_name: Name of the JSON configuration file to save the configuration to.
        """
        with open(file_name, 'w') as cf:
            json.dump(self, cf, indent=4, ensure_ascii=False)

    # noinspection PyMissingConstructor
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __getitem__(self, key: [str, tuple]):
        """Override the inherited getter.
        :param key Either a key name (string) or a tuple consisting of
          [0] Configuration key name and
          [1] Optional default value to return if the key isn't found. If not given, a new, empty Config instance will
              be inserted and returned
        :rtype : V
        :return Configuration value corresponding to the name or the default.
        """
        # Sort the arguments
        default = None
        default_given = False
        if type(key) is tuple:
            key_name = key[0]
            if len(key) > 1:
                default = key[1]
                default_given = True
        # If key is not a tuple, consider it a scalar [string] key name
        else:
            key_name = key

        # Try to fetch a key
        if key_name in self:
            return dict.__getitem__(self, key_name)

        # We don't have the key. If a default was given, return it
        if default_given:
            return default

        # Insert an empty Config instance and return it
        result = Config()
        dict.__setitem__(self, key_name, result)
        return result

    def __setitem__(self, key, value):
        """Override the inherited setter to convert incoming dict values into Config instances and to remove values when
        they are assigned None.
        """
        # A value of None means removing it
        if value is None:
            dict.__delitem__(self, key)

        else:
            # Convert dictionaries into Config instances
            if type(value) is dict:
                value = Config(value)
            dict.__setitem__(self, key, value)

    def update(self, *args, **kwargs):
        """Override to provide proper setter calls, also for the constructor."""
        # Process positional arguments (a single iterable is allowed)
        if args:
            if len(args) > 1:
                raise TypeError('update() expected at most 1 arguments, got {}'.format(len(args)))
            for k, v in dict(args[0]).items():
                self[k] = v

        # Process keyword arguments
        for k, v in kwargs.items():
            self[k] = v


class KeyboardManager:
    """Utility class for managing keyboards shortcuts. This base class binds nothing, it's used as-is when no shortcut
    backend is available; subclasses implement _bind_all() and _unbind_all().
    """

    @staticmethod
    def create(on_port_selected: callable):
        """Create and return a keyboard manager instance suitable for the current session.
        :param on_port_selected: callback that receives the port once the corresponding shortcut has been pressed
        """
        is_wayland = os.environ.get('XDG_SESSION_TYPE') == 'wayland' or 'WAYLAND_DISPLAY' in os.environ

        # On Wayland, only the portal can provide global shortcuts. On X11, prefer Keybinder as it works on any desktop
        # and binds keys without asking the user for a confirmation
        if is_wayland and PortalKeyboardManager.is_available():
            return PortalKeyboardManager(on_port_selected)
        if not is_wayland and Keybinder is not None:
            return KeybinderKeyboardManager(on_port_selected)
        if not is_wayland and PortalKeyboardManager.is_available():
            return PortalKeyboardManager(on_port_selected)

        logging.warning('No global keyboard shortcut backend available, keyboard shortcuts are disabled')
        return KeyboardManager(on_port_selected)

    def __init__(self, on_port_selected: callable):
        """Constructor.
        :param on_port_selected: callback that receives the port once the corresponding shortcut has been pressed
        """
        self.current_mappings = {}  # Dictionary of list of tuples: shortcut => [(device_name, port_name), ...]
        self.current_labels   = {}  # Dictionary of list of port display names: shortcut => [port_label, ...]
        self.on_port_selected = on_port_selected

    def _bind_all(self):
        """Bind all key bindings according to the current_mappings."""
        pass

    def _unbind_all(self):
        """Unbind all mapped key bindings."""
        pass

    def bind_keys(self, config: Config):
        """Updates key bindings based on the current configuration.
        :param config: Config object to take keyboard shortcuts from
        """
        logging.debug('%s.bind_keys()', type(self).__name__)
        new_mappings = {}
        new_labels   = {}

        # Scan all ports of all devices
        for device_name, device_cfg in config['devices'].items():
            for port_name, port_cfg in device_cfg['ports'].items():
                # If there's a shortcut
                shortcut = port_cfg['shortcut', None]
                if shortcut:
                    # Append the tuple to the mapping list for the shortcut
                    if shortcut not in new_mappings:
                        new_mappings[shortcut] = []
                        new_labels[shortcut]   = []
                    new_mappings[shortcut].append((device_name, port_name))
                    new_labels[shortcut].append(port_cfg['name', None] or port_name)

        # Sort each list by device and port name
        for m in new_mappings.values():
            m.sort()
        for l in new_labels.values():
            l.sort()

        self._rebind(new_mappings, new_labels)

    def _rebind(self, mappings: dict, labels: dict):
        """(Re)map all mappings.
        :param mappings: dictionary of list of tuples: shortcut => [(device_name, port_name), ...]
        :param labels: dictionary of list of port display names: shortcut => [port_label, ...]
        """
        self._unbind_all()
        self.current_mappings = mappings
        self.current_labels   = labels
        self._bind_all()

    def suspend(self):
        """Temporarily disable all shortcuts."""
        self._unbind_all()

    def resume(self):
        """Restore all shortcuts disabled by a call to suspend()."""
        self._bind_all()

    def shutdown(self):
        """Remove all keyboard bindings."""
        logging.debug('%s.shutdown()', type(self).__name__)
        self._unbind_all()
        self.current_mappings = {}
        self.current_labels   = {}


class KeybinderKeyboardManager(KeyboardManager):
    """Keyboard manager that grabs shortcuts using Keybinder. Only works on X11."""

    def __init__(self, on_port_selected: callable):
        super().__init__(on_port_selected)
        Keybinder.init()
        logging.debug('Using Keybinder for keyboard shortcuts')

    def _bind_all(self):
        for shortcut, mapping in self.current_mappings.items():
            if Keybinder.bind(shortcut, self.on_port_selected, mapping):
                logging.debug('  - Bound keyboard shortcut `%s` to `%s`', shortcut, mapping)
            else:
                logging.warning('Failed to bind keyboard shortcut `%s` to `%s`', shortcut, mapping)

    def _unbind_all(self):
        for shortcut in self.current_mappings.keys():
            Keybinder.unbind(shortcut)
            logging.debug('  - Unbound keyboard shortcut `%s`', shortcut)


class PortalKeyboardManager(KeyboardManager):
    """Keyboard manager that registers shortcuts via the XDG Desktop Portal GlobalShortcuts interface. Works on Wayland
    (and on X11 desktops whose portal implements it). The configured shortcut is only passed to the desktop as a
    preferred trigger: the desktop may ask the user to confirm or change it.

    Shortcut IDs registered with the portal are the configured shortcut strings, so that the desktop can remember the
    user's choice across restarts.
    """

    @staticmethod
    def is_available() -> bool:
        """Return whether the portal implements the GlobalShortcuts interface."""
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            res = bus.call_sync(
                PORTAL_BUS_NAME,
                PORTAL_OBJECT_PATH,
                'org.freedesktop.DBus.Properties',
                'Get',
                GLib.Variant('(ss)', (PORTAL_IFACE_SHORTCUT, 'version')),
                GLib.VariantType('(v)'),
                Gio.DBusCallFlags.NONE,
                2000,
                None)
            logging.debug('XDG portal GlobalShortcuts version %d found', res.unpack()[0])
            return True
        except GLib.Error as e:
            logging.debug('XDG portal GlobalShortcuts is not available: %s', e.message)
            return False

    @staticmethod
    def accelerator_to_trigger(shortcut: str):
        """Convert a Gtk accelerator name (e.g. `<Primary><Alt>1`) into an XDG shortcut trigger (e.g. `CTRL+ALT+1`).
        :return: the trigger string or None if the accelerator could not be parsed
        """
        key, mods = Gtk.accelerator_parse(shortcut)
        if not key:
            return None
        parts = []
        if mods & Gdk.ModifierType.CONTROL_MASK:
            parts.append('CTRL')
        if mods & Gdk.ModifierType.MOD1_MASK:
            parts.append('ALT')
        if mods & Gdk.ModifierType.SHIFT_MASK:
            parts.append('SHIFT')
        if mods & (Gdk.ModifierType.SUPER_MASK | Gdk.ModifierType.MOD4_MASK):
            parts.append('LOGO')
        parts.append(Gdk.keyval_name(key))
        return '+'.join(parts)

    def __init__(self, on_port_selected: callable):
        super().__init__(on_port_selected)
        self._bus            = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._sender         = self._bus.get_unique_name().lstrip(':').replace('.', '_')
        self._session_handle = None   # Handle of the current portal session, if any
        self._generation     = 0      # Incremented on each (un)bind, used to discard outdated async responses
        self._suspended      = False

        # Listen to shortcut activations
        self._bus.signal_subscribe(
            PORTAL_BUS_NAME,
            PORTAL_IFACE_SHORTCUT,
            'Activated',
            PORTAL_OBJECT_PATH,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_activated)
        logging.debug('Using XDG portal for keyboard shortcuts')

    def _portal_request(self, method: str, make_params: callable, on_response: callable):
        """Call a portal method that returns its result asynchronously via a Request object.
        :param method: GlobalShortcuts method name
        :param make_params: function that receives a handle token and returns the method parameters as a GLib.Variant
        :param on_response: function that receives the response code and the results dictionary
        """
        token = 'iss_' + uuid.uuid4().hex
        request_path = '{}/request/{}/{}'.format(PORTAL_OBJECT_PATH, self._sender, token)
        sub_id = None

        def on_signal(conn, sender, path, iface, signal, params):
            self._bus.signal_unsubscribe(sub_id)
            response, results = params.unpack()
            on_response(response, results)

        def on_call_done(bus, result):
            try:
                bus.call_finish(result)
            except GLib.Error as e:
                self._bus.signal_unsubscribe(sub_id)
                logging.warning('XDG portal call %s failed: %s', method, e.message)

        # Subscribe to the response before making the call to avoid a race
        sub_id = self._bus.signal_subscribe(
            PORTAL_BUS_NAME,
            PORTAL_IFACE_REQUEST,
            'Response',
            request_path,
            None,
            Gio.DBusSignalFlags.NONE,
            on_signal)
        self._bus.call(
            PORTAL_BUS_NAME,
            PORTAL_OBJECT_PATH,
            PORTAL_IFACE_SHORTCUT,
            method,
            make_params(token),
            GLib.VariantType('(o)'),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            on_call_done)

    def _close_session(self, session_handle: str):
        """Close the given portal session, which removes all its shortcuts."""
        self._bus.call(
            PORTAL_BUS_NAME, session_handle, PORTAL_IFACE_SESSION, 'Close', None, None, Gio.DBusCallFlags.NONE, -1,
            None, None)

    def _rebind(self, mappings: dict, labels: dict):
        # Recreating a portal session may prompt the user, so skip if nothing has changed
        if mappings == self.current_mappings and labels == self.current_labels:
            logging.debug('  - Keyboard shortcuts unchanged')
            return
        super()._rebind(mappings, labels)

    def _bind_all(self):
        self._unbind_all()
        if not self.current_mappings:
            return

        generation = self._generation
        mappings   = self.current_mappings
        shortcuts  = []
        for shortcut in mappings.keys():
            props = {'description': GLib.Variant('s', _('Switch to {}').format(', '.join(self.current_labels[shortcut])))}
            trigger = self.accelerator_to_trigger(shortcut)
            if trigger:
                props['preferred_trigger'] = GLib.Variant('s', trigger)
            shortcuts.append((shortcut, props))

        def on_bind_response(session_handle, response, results):
            if generation != self._generation:
                return
            if response != 0:
                logging.warning('XDG portal refused to bind keyboard shortcuts (response %d)', response)
                return
            for shortcut_id, props in results.get('shortcuts', []):
                logging.debug(
                    '  - Bound keyboard shortcut `%s` to `%s` (trigger: `%s`)',
                    shortcut_id, mappings.get(shortcut_id), props.get('trigger_description', ''))

        def on_session_response(response, results):
            session_handle = results.get('session_handle')
            if response != 0 or not session_handle:
                logging.warning('Failed to create XDG portal session for keyboard shortcuts (response %d)', response)
                return

            # If the mappings have changed in the meantime, drop this session
            if generation != self._generation:
                self._close_session(session_handle)
                return

            logging.debug('Created XDG portal shortcut session %s', session_handle)
            self._session_handle = session_handle
            self._portal_request(
                'BindShortcuts',
                lambda token: GLib.Variant(
                    '(oa(sa{sv})sa{sv})', (session_handle, shortcuts, '', {'handle_token': GLib.Variant('s', token)})),
                lambda resp, res: on_bind_response(session_handle, resp, res))

        self._portal_request(
            'CreateSession',
            lambda token: GLib.Variant('(a{sv})', ({
                'handle_token':         GLib.Variant('s', token),
                'session_handle_token': GLib.Variant('s', 'iss_' + uuid.uuid4().hex),
            },)),
            on_session_response)

    def _unbind_all(self):
        # Invalidate any pending requests
        self._generation += 1
        if self._session_handle:
            self._close_session(self._session_handle)
            logging.debug('Closed XDG portal shortcut session %s', self._session_handle)
            self._session_handle = None

    def _on_activated(self, conn, sender, path, iface, signal, params):
        """Signal handler: portal shortcut activated."""
        session_handle, shortcut_id, timestamp, options = params.unpack()
        if self._suspended or session_handle != self._session_handle:
            return
        mapping = self.current_mappings.get(shortcut_id)
        if mapping:
            self.on_port_selected(shortcut_id, mapping)

    def suspend(self):
        # Keep the session (recreating it may prompt the user), just ignore activations
        self._suspended = True

    def resume(self):
        self._suspended = False
