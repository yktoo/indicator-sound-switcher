from gi.repository import GObject
from . import lib_pulseaudio


class Port(GObject.GObject):
    """Generic (sink/source/card) port class."""

    def get_is_active(self):
        """is_active: defines whether the associated port is the active one for its sink/source."""
        return self._is_active

    def set_is_active(self, value: bool):
        self._is_active = value

        # If activated, also activate the item that corresponds to the port
        if self.is_active and self.menu_item:
            # Inhibit the activate event
            with self.menu_item.handler_block(self.handler_id):
                self.menu_item.set_active(True)

    is_active = GObject.property(type=bool, default=False, getter=get_is_active, setter=set_is_active)

    def get_is_available(self):
        """is_available: defines whether the associated port is the available for the user."""
        return self._is_available or self.is_dummy  # A dummy port is considered "always available"

    def set_is_available(self, value: bool):
        self._is_available = value

        # Show or hide the corresponding menu item
        if self.menu_item:
            if self.is_available:
                self.menu_item.show()
            else:
                self.menu_item.hide()

    is_available = GObject.property(type=bool, default=False, getter=get_is_available, setter=set_is_available)

    def __init__(
            self, name: str, description, display_name: str, priority: int, is_available: bool, is_visible: bool,
            direction: int, profiles):
        """Constructor.
        :param name:          (Internal) name of the port
        :param description:   Default 'human friendly' name of the port
        :param display_name:  Port display name overriden by user. If empty, description is to be used
        :param priority:      Port priority as reported by PulseAudio
        :param is_available:  Whether the port is available for the user
        :param is_visible:    Whether the port is visible for the user
        :param direction:     Port direction (input/output), one of the PA_DIRECTION_* constants
        :param profiles:      List of strings, name of the profiles that support this port
        """
        GObject.GObject.__init__(self)
        self.name          = name
        self.description   = description
        self.display_name  = display_name
        self.priority      = priority
        self._is_available = is_available
        self.is_visible    = is_visible
        self.direction     = direction
        self.profiles      = profiles

        # Initialise other properties
        # -- Owner source/sink in case this is a source/sink port, otherwise None
        self.owner_stream  = None
        # -- Owner card in case this is a card port, otherwise None
        self.onwer_card    = None
        # -- Menu item associated with this port, if any, otherwise None
        self.menu_item     = None
        # -- Property storage: is_active
        self._is_active    = False

        # Initialise derived properties
        # -- Whether it's a dummy port created for a portless device
        self.is_dummy  = description is None
        # -- Whether it's an output port
        self.is_output = direction == lib_pulseaudio.PA_DIRECTION_OUTPUT

        # Activate signal's handler ID (will be used for inhibiting the handler later)
        self.handler_id  = None

    def get_display_name(self) -> str:
        """Returns display name for the port."""
        return self.display_name or self.description

    def get_menu_item_title(self) -> str:
        """Returns the title to be used with menu item."""
        return \
            (self.owner_card.get_display_name() if self.owner_card else _('(unknown device)')) + \
            ('' if self.is_dummy else ' ‣ ' + self.get_display_name())
