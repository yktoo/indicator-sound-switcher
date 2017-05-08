from gi.repository import GObject


class Stream(GObject.GObject):
    """Base class for sink and source. Call it Stream to be consistent with Gnome Sound Panel."""

    def get_is_active(self):
        """is_active: defines whether the associated sink/source is the active (default) one."""
        return self._is_active

    def set_is_active(self, value: bool):
        self._is_active = value
        # If activated, also activate the item that corresponds to the active port
        if value:
            for port in self.ports.values():
                if port.is_active or port.is_dummy:
                    port.is_active = True
                    break

    is_active = GObject.property(type=bool, default=False, getter=get_is_active, setter=set_is_active)

    def __init__(self, index: int, name: str, display_name: str, description: str, ports: dict, card_index: int):
        """Constructor."""
        GObject.GObject.__init__(self)
        self.index        = index
        self.name         = name
        self.display_name = display_name
        self.description  = description
        self.ports        = ports
        self.card_index   = card_index
        self._is_active   = False

        # Assign every port's owner_stream
        for port in self.ports.values():
            port.owner_stream = self

    # Activates the specified port by its name
    def activate_port_by_name(self, name: str):
        for port in self.ports.values():
            port.is_active = port.name == name

    def get_display_name(self) -> str:
        """Returns display name for the stream."""
        return self.display_name or self.description


class Source(Stream):
    """Source class."""
    pass


class Sink(Stream):
    """Sink class."""
    pass
