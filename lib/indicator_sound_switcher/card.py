from gi.repository import GObject
from . import lib_pulseaudio


class CardProfile(GObject.GObject):
    """Card profile class."""

    def __init__(self, name: str, description: str, num_sinks: int, num_sources: int, priority: int, is_active: bool):
        """Constructor."""
        GObject.GObject.__init__(self)
        self.name        = name
        self.description = description
        self.num_sinks   = num_sinks
        self.num_sources = num_sources
        self.priority    = priority
        self.is_active   = is_active

    def get_id_text(self):
        """Return a descriptive identification text for the profile."""
        return '`{}` ({})'.format(self.name, self.description)


class Card(GObject.GObject):
    """Card class."""

    def __init__(self, index: int, name: str, display_name: str, driver: str, profiles: dict, ports: dict, proplist):
        """Constructor.
        :param index:         Index of the card, as provided by PulseAudio
        :param name:          (Internal) name of the card, as provided by PulseAudio
        :param display_name:  Card display name overridden by user. If empty, description is to be used
        :param driver:        Name of the driver used
        :param profiles:      Dictionary of CardProfile objects, indexed by profile name
        :param ports:         Dictionary of Port objects, indexed by port name
        :param proplist:      Property list, a PulseAudio's pa_proplist structure
        """
        GObject.GObject.__init__(self)
        self.index        = index
        self.name         = name
        self.display_name = display_name
        self.driver       = driver
        self.profiles     = profiles
        self.ports        = ports
        self.proplist     = proplist

        # Initialise derived properties
        self.description  = self.get_property_str("device.description")
        self.vendor_name  = self.get_property_str("device.vendor.name")
        self.product_name = self.get_property_str("device.product.name")

        # Assign every port's owner_card
        for port in self.ports.values():
            port.owner_card = self

    def find_stream_port(self, card_port, sources: dict, sinks: dict):
        """Try to find a sink/source port that corresponds to the given card port, belonging to this card.
        :param card_port: Card port to find a matching port for
        :param sources: List of all sources to search in case the port is an input
        :param sinks: List of all sinks to search in case the port is an output
        :returns tuple containing stream (or None) and its port (or None)
        """
        # Try to find a sink/source for this card (by matching card index)
        streams = sinks if card_port.is_output else sources
        for stream in streams.values():
            if stream.card_index == self.index:
                # Found a potential stream. Now try to find a corresponding stream's port (with the matching port name).
                if card_port.name in stream.ports:
                    return stream, stream.ports[card_port.name]

        # No luck
        return None, None

    def get_active_profile(self) -> CardProfile | None:
        """Returns the currently active profile on the card, if any, otherwise None."""
        for profile in self.profiles.values():
            if profile.is_active:
                return profile
        return None

    def get_property_str(self, name: str) -> str:
        """Returns value of a property by its name as a string."""
        v = lib_pulseaudio.pa_proplist_gets(self.proplist, name.encode())
        return v.decode() if v else _('(none)')

    def get_display_name(self) -> str:
        """Returns display name for the card."""
        return self.display_name or self.description

    def get_descriptive_name(self) -> str:
        """Return a 'descriptive' name for the card, which consists of the name of an available output port with the
        highest priority (this is the behaviour Gnome Sound Panel implements) and the card's description."""
        max_port = None
        for port in self.ports.values():
            if port.is_available and port.is_output and (max_port is None or port.priority > max_port.priority):
                max_port = port

        # If a suitable port found, return it combined with the description, otherwise just use the description
        return '{} - {}'.format(max_port.description, self.description) if max_port else self.description

    def update_port_activity(self, sources: dict, sinks: dict):
        """Updates the is_active state of every port on the card, according to the state of the related sink/source
        port, if any.
        """
        for port in self.ports.values():
            # Try to find a sink/source port for this port
            stream, stream_port = self.find_stream_port(port, sources, sinks)

            # Update the port object (this will also update the menu item). A port is active if it's mapped to an
            # active stream and is dummy or its corresponding stream's port is active
            port.is_active = \
                stream is not None and \
                stream.is_active and \
                stream_port is not None and \
                (port.is_dummy or stream_port.is_active)
