#!/usr/bin/env python3

from distutils.core import setup
import os


data_files = [
    # App shortcut
    ('share/applications',                      ['indicator-sound-switcher.desktop']),

    # Autostart entry
    ('/etc/xdg/autostart',                      ['indicator-sound-switcher.desktop']),

    # Icons
    ('share/icons/ubuntu-mono-dark/status/22',  ['icons/ubuntu-mono-dark/indicator-sound-switcher.svg']),
    ('share/icons/ubuntu-mono-light/status/22', ['icons/ubuntu-mono-light/indicator-sound-switcher.svg']),
    ('share/icons/hicolor/22x22/status',        ['icons/default/indicator-sound-switcher.svg']),

    # Manpage
    ('share/man/man1',                          ['man/indicator-sound-switcher.1']),
]

# Add all available .mo translation files to the list data files
for lang in os.listdir('locale'):
    data_files.append(
        (
            'share/locale/{}/LC_MESSAGES'.format(lang),
            [os.path.join('locale', lang, 'LC_MESSAGES', 'indicator-sound-switcher.mo')]
        )
    )

# Configure
setup(
    name='indicator-sound-switcher',
    version='2.0.2ubuntu0',
    description='Sound input/output selector indicator',
    author='Dmitry Kann',
    author_email='yktooo@gmail.com',
    url='https://github.com/yktoo/indicator-sound-switcher',
    license='GPL3',
    package_dir={'': 'lib'},
    packages=['indicator_sound_switcher'],
    scripts=['indicator-sound-switcher'],
    data_files=data_files,
)
