#!/usr/bin/env python

from distutils.core import setup

setup(
    name='indicator-sound-switcher',
    version='1.2.1ubuntu0-gtk2ppa0-1',
    description='Sound input/output selector indicator',
    author='Dmitry Kann',
    author_email='yktooo@gmail.com',
    url='https://github.com/yktoo/indicator-sound-switcher',
    license='GPL3',
    package_dir={'': 'lib'},
    packages=['indicator_sound_switcher'],
    scripts=['indicator-sound-switcher'],
    data_files=[
        ('/usr/share/applications',                      ['indicator-sound-switcher.desktop']),
        ('/etc/xdg/autostart',                           ['indicator-sound-switcher.desktop']),
        ('/usr/share/icons/ubuntu-mono-dark/status/22',  ['icons/ubuntu-mono-dark/indicator-sound-switcher.svg']),
        ('/usr/share/icons/ubuntu-mono-light/status/22', ['icons/ubuntu-mono-light/indicator-sound-switcher.svg']),
        ('/usr/share/icons/hicolor/22x22/status',        ['icons/default/indicator-sound-switcher.svg']),
    ]
)
