"""
Tests for the Config class.
"""
import json

import pytest

from indicator_sound_switcher.config import Config


class TestConstruction:

    def test_empty(self):
        c = Config()
        assert c == {}
        assert isinstance(c, dict)

    def test_from_dict(self):
        c = Config({'a': 1, 'b': 'x'})
        assert c == {'a': 1, 'b': 'x'}

    def test_from_kwargs(self):
        c = Config(a=1, b='x')
        assert c == {'a': 1, 'b': 'x'}

    def test_from_pairs(self):
        c = Config([('a', 1), ('b', 2)])
        assert c == {'a': 1, 'b': 2}

    def test_nested_dicts_converted(self):
        c = Config({'devices': {'card': {'ports': {'p1': {'name': 'Speakers'}}}}})
        assert type(c['devices'])                         is Config
        assert type(c['devices']['card'])                 is Config
        assert type(c['devices']['card']['ports'])        is Config
        assert type(c['devices']['card']['ports']['p1'])  is Config
        assert c['devices']['card']['ports']['p1']['name'] == 'Speakers'

    def test_none_value_raises(self):
        # Assigning None removes a key, so the key must exist first: in a constructor it doesn't
        with pytest.raises(KeyError):
            Config({'a': None})

    def test_update_too_many_args(self):
        with pytest.raises(TypeError):
            Config().update({'a': 1}, {'b': 2})


class TestGetItem:

    def test_existing_key(self):
        c = Config(a=1)
        assert c['a'] == 1

    def test_existing_key_ignores_default(self):
        c = Config(a=1)
        assert c['a', 42] == 1

    def test_existing_falsy_value_ignores_default(self):
        c = Config(a=False, b=0, e='')
        assert c['a', True] is False
        assert c['b', 1]    == 0
        assert c['e', 'x']  == ''

    def test_missing_key_with_default(self):
        c = Config()
        assert c['a', 42] == 42

    def test_missing_key_with_none_default(self):
        c = Config()
        assert c['a', None] is None

    def test_missing_key_with_default_does_not_insert(self):
        c = Config()
        _ = c['a', 42]
        assert 'a' not in c

    def test_missing_key_autocreates(self):
        c = Config()
        sub = c['a']
        assert type(sub) is Config
        assert sub == {}
        assert 'a' in c
        assert c['a'] is sub

    def test_missing_key_single_element_tuple_autocreates(self):
        c = Config()
        sub = c['a', ]
        assert type(sub) is Config
        assert 'a' in c

    def test_autocreated_chain(self):
        c = Config()
        c['devices']['card']['ports']['p1']['name'] = 'Speakers'
        assert c == {'devices': {'card': {'ports': {'p1': {'name': 'Speakers'}}}}}

    def test_get_does_not_autocreate(self):
        # dict.get() isn't overridden
        c = Config()
        assert c.get('a') is None
        assert 'a' not in c


class TestSetItem:

    def test_set_scalar(self):
        c = Config()
        c['a'] = 1
        assert c['a'] == 1

    def test_set_none_deletes(self):
        c = Config(a=1, b=2)
        c['a'] = None
        assert c == {'b': 2}

    def test_set_none_missing_key_raises(self):
        c = Config()
        with pytest.raises(KeyError):
            c['a'] = None

    def test_set_dict_converted(self):
        c = Config()
        c['a'] = {'b': {'c': 1}}
        assert type(c['a'])      is Config
        assert type(c['a']['b']) is Config

    def test_set_config_kept_as_is(self):
        c = Config()
        sub = Config(x=1)
        c['a'] = sub
        assert c['a'] is sub

    def test_dicts_in_lists_not_converted(self):
        c = Config()
        c['a'] = [{'b': 1}]
        assert type(c['a'][0]) is dict

    def test_update_converts(self):
        c = Config(a=1)
        c.update({'b': {'c': 1}}, d={'e': 2})
        assert c == {'a': 1, 'b': {'c': 1}, 'd': {'e': 2}}
        assert type(c['b']) is Config
        assert type(c['d']) is Config

    def test_update_none_deletes(self):
        c = Config(a=1, b=2)
        c.update(a=None)
        assert c == {'b': 2}


class TestFile:

    def test_load_missing_file(self, tmp_path):
        c = Config.load_from_file(str(tmp_path / 'missing.json'))
        assert type(c) is Config
        assert c == {}

    def test_load(self, tmp_path):
        f = tmp_path / 'config.json'
        f.write_text(json.dumps({
            'show_inputs': False,
            'devices': {'card': {'name': 'My card', 'ports': {'p1': {'shortcut': '<Super>1'}}}},
            'list': [{'a': 1}],
        }))
        c = Config.load_from_file(str(f))
        assert type(c) is Config
        assert c['show_inputs', True] is False
        assert type(c['devices']['card']) is Config
        assert c['devices']['card']['ports']['p1']['shortcut', None] == '<Super>1'
        # Unlike assignment, loading converts dicts nested in lists, too
        assert type(c['list'][0]) is Config

    def test_load_invalid_json(self, tmp_path):
        f = tmp_path / 'config.json'
        f.write_text('{not json')
        with pytest.raises(json.JSONDecodeError):
            Config.load_from_file(str(f))

    def test_save(self, tmp_path):
        f = tmp_path / 'config.json'
        Config({'a': 1, 'b': {'c': 'Динамики'}}).save_to_file(str(f))
        text = f.read_text(encoding='utf-8')
        # Non-ASCII is written as-is, and the output is indented
        assert 'Динамики' in text
        assert '\n    "a": 1' in text
        assert json.loads(text) == {'a': 1, 'b': {'c': 'Динамики'}}

    def test_round_trip(self, tmp_path):
        f = tmp_path / 'config.json'
        c = Config()
        c['show_outputs'] = False
        c['devices']['card']['ports']['p1']['visible'] = False
        c['devices']['card']['ports']['p1']['preferred_profile'] = 'a2dp-sink'
        c.save_to_file(str(f))

        loaded = Config.load_from_file(str(f))
        assert loaded == c
        assert type(loaded['devices']['card']['ports']['p1']) is Config

    def test_save_overwrites(self, tmp_path):
        f = tmp_path / 'config.json'
        Config(a=1, b=2).save_to_file(str(f))
        Config(c=3).save_to_file(str(f))
        assert Config.load_from_file(str(f)) == {'c': 3}
