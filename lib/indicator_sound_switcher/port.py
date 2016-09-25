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

    def __init__(self, name: str, description, priority: int, is_available: bool, direction: int, profiles):
        """Constructor."""
        GObject.GObject.__init__(self)
        self.name          = name
        self.description   = description
        self.priority      = priority
        self._is_available = is_available
        self.direction     = direction
        self.profiles      = profiles

        # Initialise other properties
        self.owner_stream  = None
        self.onwer_card    = None
        self.menu_item     = None
        self._is_active    = False

        # Initialise derived properties
        self.is_dummy  = description is None
        self.is_output = direction == lib_pulseaudio.PA_DIRECTION_OUTPUT

        # Activate signal's handler ID (will be used for inhibiting the handler later)
        self.handler_id  = None

    def get_menu_item_title(self):
        """Returns the title to be used with menu item."""
        return \
            (self.owner_card.description if self.owner_card else '(unknown device)') + \
            ('' if self.is_dummy else ' ‣ ' + self.description)
