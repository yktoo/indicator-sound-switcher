#!/usr/bin/env python3

from distutils.core import setup, Command
import os

package_name = 'indicator-sound-switcher'


def generate_translation_files():
    """Returns the list of .mo translation data files."""
    lang_files = [
        (
            'share/locale/{}/LC_MESSAGES'.format(lang),
            [os.path.join('locale', lang, 'LC_MESSAGES', package_name + '.mo')]
        ) for lang in os.listdir('locale')
    ]

    return lang_files


setup(
    name=package_name,
    version='2.0.2ubuntu0',
    description='Sound input/output selector indicator',
    author='Dmitry Kann',
    author_email='yktooo@gmail.com',
    url='https://github.com/yktoo/indicator-sound-switcher',
    license='GPL3',
    package_dir={'': 'lib'},
    packages=['indicator_sound_switcher'],
    scripts=['indicator-sound-switcher'],
    data_files=[
        ('share/applications',                      ['indicator-sound-switcher.desktop']),
        ('/etc/xdg/autostart',                      ['indicator-sound-switcher.desktop']),
        ('share/icons/ubuntu-mono-dark/status/22',  ['icons/ubuntu-mono-dark/indicator-sound-switcher.svg']),
        ('share/icons/ubuntu-mono-light/status/22', ['icons/ubuntu-mono-light/indicator-sound-switcher.svg']),
        ('share/icons/hicolor/22x22/status',        ['icons/default/indicator-sound-switcher.svg']),
    ] + generate_translation_files(),
)
