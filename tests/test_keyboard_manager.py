"""
Tests for KeyboardManager.bind_keys().
"""
from indicator_sound_switcher.config import Config, KeyboardManager, PortalKeyboardManager


class RecordingKeyboardManager(KeyboardManager):
    """Keyboard manager that records (un)bind calls along with the mappings current at the time of the call."""

    def __init__(self):
        super().__init__(on_port_selected=lambda *args: None)
        self.calls = []

    def _bind_all(self):
        self.calls.append(('bind', self.current_mappings))

    def _unbind_all(self):
        self.calls.append(('unbind', self.current_mappings))


class RecordingPortalKeyboardManager(PortalKeyboardManager):
    """Portal keyboard manager that doesn't talk to D-Bus, used to test its _rebind() override."""

    # noinspection PyMissingConstructor
    def __init__(self):
        KeyboardManager.__init__(self, on_port_selected=lambda *args: None)
        self.calls = []

    def _bind_all(self):
        self.calls.append(('bind', self.current_mappings))

    def _unbind_all(self):
        self.calls.append(('unbind', self.current_mappings))


def make_config(devices: dict) -> Config:
    return Config({'devices': devices})


class TestMappings:

    def test_empty_config(self):
        km = RecordingKeyboardManager()
        km.bind_keys(Config())
        assert km.current_mappings == {}
        assert km.current_labels   == {}

    def test_no_shortcuts(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({'card': {'ports': {'p1': {'name': 'Speakers', 'visible': False}}}}))
        assert km.current_mappings == {}
        assert km.current_labels   == {}

    def test_single_shortcut(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1', 'name': 'Speakers'}}}}))
        assert km.current_mappings == {'<Super>1': [('card', 'p1')]}
        assert km.current_labels   == {'<Super>1': ['Speakers']}

    def test_label_falls_back_to_port_name(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({
            'card': {'ports': {
                'p1': {'shortcut': '<Super>1'},
                'p2': {'shortcut': '<Super>2', 'name': ''},
            }},
        }))
        assert km.current_labels == {'<Super>1': ['p1'], '<Super>2': ['p2']}

    def test_empty_shortcut_ignored(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({'card': {'ports': {'p1': {'shortcut': ''}}}}))
        assert km.current_mappings == {}

    def test_distinct_shortcuts(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({
            'card1': {'ports': {'p1': {'shortcut': '<Super>1'}, 'p2': {'shortcut': '<Super>2'}}},
            'card2': {'ports': {'p1': {'shortcut': '<Super>3'}}},
        }))
        assert km.current_mappings == {
            '<Super>1': [('card1', 'p1')],
            '<Super>2': [('card1', 'p2')],
            '<Super>3': [('card2', 'p1')],
        }

    def test_shared_shortcut_sorted(self):
        # Ports sharing a shortcut are toggled between, in device then port name order
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({
            'card2': {'ports': {'b': {'shortcut': '<Super>1', 'name': 'Alpha'}}},
            'card1': {'ports': {
                'z': {'shortcut': '<Super>1', 'name': 'Charlie'},
                'a': {'shortcut': '<Super>1', 'name': 'Bravo'},
            }},
        }))
        assert km.current_mappings == {'<Super>1': [('card1', 'a'), ('card1', 'z'), ('card2', 'b')]}
        # Labels are sorted on their own, so they don't necessarily follow the mapping order
        assert km.current_labels   == {'<Super>1': ['Alpha', 'Bravo', 'Charlie']}

    def test_device_without_ports(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({'card1': {'name': 'My card'}, 'card2': {'ports': {'p1': {'shortcut': 'F9'}}}}))
        assert km.current_mappings == {'F9': [('card2', 'p1')]}

    def test_config_autocreated_sections(self):
        # Reading the config auto-creates missing sections, which then end up in the saved config file
        config = make_config({'card': {'name': 'My card'}})
        RecordingKeyboardManager().bind_keys(config)
        assert config == {'devices': {'card': {'name': 'My card', 'ports': {}}}}

        config = Config()
        RecordingKeyboardManager().bind_keys(config)
        assert config == {'devices': {}}


class TestRebinding:

    def test_unbinds_old_then_binds_new(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1'}}}}))
        km.calls.clear()

        km.bind_keys(make_config({'card': {'ports': {'p1': {'shortcut': '<Super>2'}}}}))
        assert km.calls == [
            ('unbind', {'<Super>1': [('card', 'p1')]}),
            ('bind',   {'<Super>2': [('card', 'p1')]}),
        ]

    def test_shortcut_removed(self):
        km = RecordingKeyboardManager()
        config = make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1'}}}})
        km.bind_keys(config)

        config['devices']['card']['ports']['p1']['shortcut'] = None
        km.bind_keys(config)
        assert km.current_mappings == {}
        assert km.current_labels   == {}

    def test_rebinds_when_unchanged(self):
        # The base class doesn't check for changes
        km = RecordingKeyboardManager()
        config = make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1'}}}})
        km.bind_keys(config)
        km.calls.clear()

        km.bind_keys(config)
        assert [c[0] for c in km.calls] == ['unbind', 'bind']

    def test_suspend_resume(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1'}}}}))
        km.calls.clear()

        km.suspend()
        km.resume()
        mappings = {'<Super>1': [('card', 'p1')]}
        assert km.calls == [('unbind', mappings), ('bind', mappings)]
        assert km.current_mappings == mappings

    def test_shutdown(self):
        km = RecordingKeyboardManager()
        km.bind_keys(make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1'}}}}))
        km.calls.clear()

        km.shutdown()
        assert km.calls == [('unbind', {'<Super>1': [('card', 'p1')]})]
        assert km.current_mappings == {}
        assert km.current_labels   == {}


class TestPortalRebinding:

    def test_skips_when_unchanged(self):
        km = RecordingPortalKeyboardManager()
        config = make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1', 'name': 'Speakers'}}}})
        km.bind_keys(config)
        km.calls.clear()

        km.bind_keys(config)
        assert km.calls == []

    def test_rebinds_when_label_changed(self):
        # Labels are part of the shortcut description shown by the desktop, so a rename requires rebinding
        km = RecordingPortalKeyboardManager()
        config = make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1', 'name': 'Speakers'}}}})
        km.bind_keys(config)
        km.calls.clear()

        config['devices']['card']['ports']['p1']['name'] = 'Headphones'
        km.bind_keys(config)
        assert [c[0] for c in km.calls] == ['unbind', 'bind']
        assert km.current_labels == {'<Super>1': ['Headphones']}

    def test_rebinds_when_mapping_changed(self):
        km = RecordingPortalKeyboardManager()
        config = make_config({'card': {'ports': {'p1': {'shortcut': '<Super>1'}}}})
        km.bind_keys(config)
        km.calls.clear()

        config['devices']['card']['ports']['p2'] = {'shortcut': '<Super>1'}
        km.bind_keys(config)
        assert [c[0] for c in km.calls] == ['unbind', 'bind']
        assert km.current_mappings == {'<Super>1': [('card', 'p1'), ('card', 'p2')]}
