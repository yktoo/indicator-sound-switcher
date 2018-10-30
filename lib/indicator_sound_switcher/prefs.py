import abc
import logging

from gi.repository import Gtk


class PreferencesDialog(Gtk.Dialog):
    """Indicator preferences dialog."""

    def __init__(self, parent: Gtk.Window=None):
        """Constructor.
        :param parent: parent window
        """
        Gtk.Dialog.__init__(
            self,
            _('Preferences'),
            parent,
            0,
            (Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_border_width(12)
        self.set_default_size(500,  300)

        # Add notebook with pages
        notebook = MainNotebook()
        self.get_content_area().pack_start(notebook, True, True, 0)

        # Show all controls
        self.show_all()


class MainNotebook(Gtk.Notebook):
    """Implementation of the preferences dialog's notebook control."""

    def __init__(self):
        super().__init__()
        logging.debug('Creating ' + self.__class__.__name__)

        # Create notebook pages
        self._add_page(GeneralPage())
        self._add_page(DevicesPage())

        # Connect page switch signal
        self.connect('switch-page', self.on_switch_page)

    def _add_page(self, page):
        """Add a single (descendant of) BasePage."""
        self.append_page(page, page.get_label_widget())

    @staticmethod
    def on_switch_page(widget, page, index):
        """Signal handler: current page changed"""
        logging.debug('Page changed to %d', index)
        page.on_activate()


class BasePage(Gtk.Box):
    """Base abstract class for notebook page objects."""

    def __init__(self, title: str, icon: str):
        """Constructor."""
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(6)
        self.set_border_width(10)
        self.scroll_box = None
        self.is_initialised = False
        self.title = title
        self.icon = icon

    def get_label_widget(self):
        """Create and return a widget for the page label."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(Gtk.Image.new_from_icon_name(self.icon, Gtk.IconSize.MENU), False, False, 0)
        box.pack_start(Gtk.Label(self.title), False, False, 0)
        box.show_all()
        return box

    def on_activate(self):
        """Is called whenever the page is activated."""
        if not self.is_initialised:
            self.is_initialised = True

            # Create a scrollbox
            self.scroll_box = Gtk.ScrolledWindow()
            self.pack_start(self.scroll_box, True, True, 0)

            # Insert the main widget
            self.scroll_box.add(self.get_content_widget())

            # Show all child widgets
            self.show_all()

            # Call the page-specific initialisation
            self.initialise()

    @abc.abstractmethod
    def initialise(self):
        """Must initialise the page."""

    @abc.abstractmethod
    def get_content_widget(self):
        """Must create and return the main widget of the page."""


class GeneralPage(BasePage):
    """General page object."""

    def __init__(self):
        super().__init__(_('General'), 'gtk-info')
        # TODO

    def initialise(self):
        pass
        # TODO

    def get_content_widget(self):
        return Gtk.Label('# TODO #')


class DevicesPage(BasePage):
    """Devices page object."""

    def __init__(self):
        super().__init__(_('Devices'), 'gtk-execute')
        # TODO

    def initialise(self):
        pass
        # TODO

    def get_content_widget(self):
        return Gtk.Label('# TODO #')
