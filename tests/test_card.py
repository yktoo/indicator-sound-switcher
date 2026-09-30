"""
Tests for the Card and CardProfile classes.
"""
import pytest

from indicator_sound_switcher import lib_pulseaudio
from indicator_sound_switcher.card import Card, CardProfile
from indicator_sound_switcher.port import Port
from indicator_sound_switcher.stream import Sink, Source

OUT = lib_pulseaudio.PA_DIRECTION_OUTPUT
IN  = lib_pulseaudio.PA_DIRECTION_INPUT


@pytest.fixture
def proplist():
    """Factory of PulseAudio property lists, freed after the test."""
    created = []

    def make(**props):
        pl = lib_pulseaudio.pa_proplist_new()
        created.append(pl)
        for name, value in props.items():
            lib_pulseaudio.pa_proplist_sets(pl, name.replace('_', '.').encode(), value.encode())
        return pl

    yield make
    for pl in created:
        lib_pulseaudio.pa_proplist_free(pl)


@pytest.fixture
def make_card(proplist):
    """Factory of cards with the given ports and profiles."""
    def make(ports=(), profiles=(), index=1, display_name='', description='Built-in Audio'):
        return Card(
            index, 'alsa_card.test', display_name, 'module-alsa-card.c',
            {p.name: p for p in profiles},
            {p.name: p for p in ports},
            proplist(device_description=description))
    return make


def port(name, direction=OUT, description='', priority=0, available=True):
    """Create a port. description=None makes a dummy port."""
    return Port(
        name, name.capitalize() if description == '' else description, '', priority, available, True, direction,
        None, None, False)


def profile(name, is_active=False):
    return CardProfile(name, name.capitalize(), 1, 1, 0, is_active)


def sink(ports, card_index=1, index=0, is_active=True):
    s = Sink(index, 'sink{}'.format(index), '', 'Sink', {p.name: p for p in ports}, card_index)
    s.is_active = is_active
    return s


def source(ports, card_index=1, index=0, is_active=True):
    s = Source(index, 'source{}'.format(index), '', 'Source', {p.name: p for p in ports}, card_index)
    s.is_active = is_active
    return s


def streams(*items):
    return {s.index: s for s in items}


class TestCardProfile:

    def test_id_text(self):
        assert CardProfile('a2dp-sink', 'High Fidelity Playback', 1, 0, 40, True).get_id_text() == \
            '`a2dp-sink` (High Fidelity Playback)'


class TestCardProperties:

    def test_properties_from_proplist(self, proplist):
        card = Card(1, 'alsa_card.test', '', 'module-alsa-card.c', {}, {}, proplist(
            device_description='Built-in Audio', device_vendor_name='Intel', device_product_name='HDA'))
        assert card.description  == 'Built-in Audio'
        assert card.vendor_name  == 'Intel'
        assert card.product_name == 'HDA'

    def test_missing_properties(self, proplist):
        card = Card(1, 'alsa_card.test', '', 'module-alsa-card.c', {}, {}, proplist())
        assert card.description  == '(none)'
        assert card.vendor_name  == '(none)'
        assert card.product_name == '(none)'

    def test_get_property_str(self, proplist):
        card = Card(1, 'alsa_card.test', '', 'module-alsa-card.c', {}, {}, proplist(device_bus='usb'))
        assert card.get_property_str('device.bus')  == 'usb'
        assert card.get_property_str('device.form') == '(none)'

    def test_ports_get_owner(self, make_card):
        p1, p2 = port('speaker'), port('mic', IN)
        card = make_card(ports=[p1, p2])
        assert p1.owner_card is card
        assert p2.owner_card is card

    def test_display_name_from_description(self, make_card):
        assert make_card(description='Built-in Audio').get_display_name() == 'Built-in Audio'

    def test_display_name_overridden(self, make_card):
        assert make_card(display_name='Laptop', description='Built-in Audio').get_display_name() == 'Laptop'


class TestActiveProfile:

    def test_active(self, make_card):
        card = make_card(profiles=[profile('off'), profile('stereo', is_active=True), profile('surround')])
        assert card.get_active_profile().name == 'stereo'

    def test_none_active(self, make_card):
        assert make_card(profiles=[profile('off'), profile('stereo')]).get_active_profile() is None

    def test_no_profiles(self, make_card):
        assert make_card().get_active_profile() is None


class TestDescriptiveName:

    def test_highest_priority_output(self, make_card):
        card = make_card(ports=[
            port('speaker',    description='Speakers',   priority=100),
            port('headphones', description='Headphones', priority=200),
        ])
        assert card.get_descriptive_name() == 'Headphones - Built-in Audio'

    def test_ignores_unavailable_ports(self, make_card):
        card = make_card(ports=[
            port('speaker',    description='Speakers',   priority=100),
            port('headphones', description='Headphones', priority=200, available=False),
        ])
        assert card.get_descriptive_name() == 'Speakers - Built-in Audio'

    def test_ignores_inputs(self, make_card):
        card = make_card(ports=[
            port('speaker', description='Speakers', priority=100),
            port('mic',     description='Mic',      priority=200, direction=IN),
        ])
        assert card.get_descriptive_name() == 'Speakers - Built-in Audio'

    def test_no_suitable_port(self, make_card):
        card = make_card(ports=[
            port('headphones', description='Headphones', available=False),
            port('mic',        description='Mic',        direction=IN),
        ])
        assert card.get_descriptive_name() == 'Built-in Audio'

    def test_no_ports(self, make_card):
        assert make_card().get_descriptive_name() == 'Built-in Audio'

    def test_dummy_ports_only(self, make_card):
        # Cards without ports (typically Bluetooth) get dummy ones
        card = make_card(ports=[
            port('#dummy_out', description=None, priority=-1),
            port('#dummy_in',  description=None, priority=-1, direction=IN),
        ])
        assert card.get_descriptive_name() == 'Built-in Audio'


class TestFindStreamPort:

    def test_output_in_sinks(self, make_card):
        p = port('speaker')
        card = make_card(ports=[p])
        sp = port('speaker')
        s = sink([sp])
        assert card.find_stream_port(p, sources={}, sinks=streams(s)) == (s, sp)

    def test_input_in_sources(self, make_card):
        p = port('mic', IN)
        card = make_card(ports=[p])
        sp = port('mic', IN)
        s = source([sp])
        # A sink with a same-named port is ignored
        assert card.find_stream_port(p, sources=streams(s), sinks=streams(sink([port('mic')]))) == (s, sp)

    def test_other_card_ignored(self, make_card):
        p = port('speaker')
        card = make_card(ports=[p], index=1)
        assert card.find_stream_port(p, sources={}, sinks=streams(sink([port('speaker')], card_index=2))) == \
            (None, None)

    def test_port_not_in_stream(self, make_card):
        p = port('headphones')
        card = make_card(ports=[p])
        assert card.find_stream_port(p, sources={}, sinks=streams(sink([port('speaker')]))) == (None, None)

    def test_searches_all_card_streams(self, make_card):
        # E.g. an HDMI card exposing several sinks: the one with the port must be found
        p = port('hdmi-output-1')
        card = make_card(ports=[p])
        sp = port('hdmi-output-1')
        s1 = sink([port('hdmi-output-0')], index=0)
        s2 = sink([sp], index=1)
        assert card.find_stream_port(p, sources={}, sinks=streams(s1, s2)) == (s2, sp)

    def test_no_streams(self, make_card):
        p = port('speaker')
        assert make_card(ports=[p]).find_stream_port(p, sources={}, sinks={}) == (None, None)


class TestUpdatePortActivity:

    def test_active_stream_active_port(self, make_card):
        speaker, headphones = port('speaker'), port('headphones')
        card = make_card(ports=[speaker, headphones])
        sp_speaker, sp_headphones = port('speaker'), port('headphones')
        s = sink([sp_speaker, sp_headphones])
        s.activate_port_by_name('headphones')

        card.update_port_activity(sources={}, sinks=streams(s))
        assert speaker.is_active    is False
        assert headphones.is_active is True

    def test_inactive_stream(self, make_card):
        speaker = port('speaker')
        card = make_card(ports=[speaker])
        sp = port('speaker')
        s = sink([sp], is_active=False)
        s.activate_port_by_name('speaker')

        card.update_port_activity(sources={}, sinks=streams(s))
        assert speaker.is_active is False

    def test_no_stream(self, make_card):
        # E.g. the port belongs to a profile that isn't active
        speaker = port('speaker')
        speaker.is_active = True
        card = make_card(ports=[speaker])

        card.update_port_activity(sources={}, sinks={})
        assert speaker.is_active is False

    def test_deactivates_previously_active(self, make_card):
        speaker, headphones = port('speaker'), port('headphones')
        card = make_card(ports=[speaker, headphones])
        s = sink([port('speaker'), port('headphones')])

        s.activate_port_by_name('speaker')
        card.update_port_activity(sources={}, sinks=streams(s))
        assert (speaker.is_active, headphones.is_active) == (True, False)

        s.activate_port_by_name('headphones')
        card.update_port_activity(sources={}, sinks=streams(s))
        assert (speaker.is_active, headphones.is_active) == (False, True)

    def test_inputs_and_outputs(self, make_card):
        speaker, mic = port('speaker'), port('mic', IN)
        card = make_card(ports=[speaker, mic])
        si = sink([port('speaker')])
        so = source([port('mic', IN)])
        si.activate_port_by_name('speaker')
        so.activate_port_by_name('mic')

        card.update_port_activity(sources=streams(so), sinks=streams(si))
        assert speaker.is_active is True
        assert mic.is_active     is True

    def test_dummy_port_follows_stream(self, make_card):
        # A dummy port is active whenever its stream is, regardless of the stream port's state
        dummy_out = port('#dummy_out', description=None)
        card = make_card(ports=[dummy_out])
        sp = port('#dummy_out', description=None)
        s = sink([sp], is_active=False)
        assert sp.is_active is False

        s.is_active = True
        sp.is_active = False
        card.update_port_activity(sources={}, sinks=streams(s))
        assert dummy_out.is_active is True

        s.is_active = False
        card.update_port_activity(sources={}, sinks=streams(s))
        assert dummy_out.is_active is False
