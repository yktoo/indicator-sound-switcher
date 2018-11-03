import abc
import logging

from gi.repository import Gtk

from .config import Config


class PreferencesDialog(Gtk.Dialog):
    """Indicator preferences dialog."""

    def __init__(self, config: Config, on_refresh: callable, parent: Gtk.Window=None):
        """Constructor.
        :param parent: parent window
        """
        Gtk.Dialog.__init__(self, _('Sound Switcher Indicator Preferences'), parent, 0, (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.set_border_width(12)
        self.set_default_size(500,  300)
        self.config = config
        self.on_refresh = on_refresh

        # Add notebook with pages
        notebook = MainNotebook(self)
        self.get_content_area().pack_start(notebook, True, True, 0)

        # Show all controls
        self.show_all()


class BasePage(Gtk.Box):
    """Base abstract class for notebook page objects."""

    def __init__(self, title: str, dlg: PreferencesDialog):
        """Constructor."""
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(6)
        self.set_border_width(10)
        self.scroll_box = None
        self.is_initialised = False
        self.title = title
        self.dlg = dlg

    def get_label_widget(self):
        """Create and return a widget for the page label."""
        return Gtk.Label.new_with_mnemonic(self.title)

    def on_activate(self):
        """Is called whenever the page is activated."""
        if not self.is_initialised:
            # Call the page-specific initialisation
            self.initialise()
            self.is_initialised = True

            # Show all child widgets
            self.show_all()

    @abc.abstractmethod
    def initialise(self):
        """Must initialise the page."""


class GeneralPage(BasePage):
    """General page object."""

    def __init__(self, dlg: PreferencesDialog):
        super().__init__(_('_General'), dlg)

        # Add switches
        self.switch_inputs  = self._add_switch(_('Show inputs'), self.on_switch_inputs_set)
        self.switch_outputs = self._add_switch(_('Show outputs'), self.on_switch_outputs_set)

    def _add_switch(self, label: str, on_state_set: callable) -> Gtk.Switch:
        """Add a new labeled switch widget to the page.
        :return: the created switch widget
        """
        # Add a horizontal box that will hold a label and a switch
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Add a label
        box.pack_start(Gtk.Label(label), False, False, 0)

        # Add a switch
        switch = Gtk.Switch()
        switch.connect('state-set', on_state_set)
        box.pack_end(switch, False, False, 0)

        # Add the box to the page
        self.pack_start(box, False, False, 0)
        return switch

    def initialise(self):
        self.switch_inputs.set_active (self.dlg.config['show_inputs',  True])
        self.switch_outputs.set_active(self.dlg.config['show_outputs', True])

    def on_switch_inputs_set(self, widget: Gtk.Switch, data):
        """Signal handler: Show Inputs switch set."""
        if not self.is_initialised:
            return
        logging.debug('.on_switch_inputs_set(%s)', widget.get_active())
        self.dlg.config['show_inputs'] = widget.get_active()
        self.dlg.on_refresh()

    def on_switch_outputs_set(self, widget: Gtk.Switch, data):
        """Signal handler: Show Outputs switch set."""
        if not self.is_initialised:
            return
        logging.debug('.on_switch_outputs_set(%s)', widget.get_active())
        self.dlg.config['show_outputs'] = widget.get_active()
        self.dlg.on_refresh()


class DevicesPage(BasePage):
    """Devices page object."""

    def __init__(self, dlg: PreferencesDialog):
        super().__init__(_('_Devices'), dlg)
        scrollbox = Gtk.ScrolledWindow()
        self.pack_start(scrollbox, True, True, 0)

    def initialise(self):
        pass
        # TODO


class MainNotebook(Gtk.Notebook):
    """Implementation of the preferences dialog's notebook control."""

    def __init__(self, dlg: PreferencesDialog):
        logging.debug('Creating ' + self.__class__.__name__)
        super().__init__()

        # Create notebook pages
        self._add_page(GeneralPage(dlg))
        self._add_page(DevicesPage(dlg))

        # Connect page switch signal
        self.connect('switch-page', self.on_switch_page)

    def _add_page(self, page: BasePage):
        """Add a single (descendant of) BasePage."""
        self.append_page(page, page.get_label_widget())

    @staticmethod
    def on_switch_page(widget, page, index):
        """Signal handler: current page changed"""
        logging.debug('Page changed to %d', index)
        page.on_activate()
