#!/usr/bin/env python

from distutils.core import setup

setup(
    name='indicator-sound-switcher',
    version='1.0.0',
    description='Sound input/output selector indicator',
    author='Dmitry Kann',
    author_email='yktooo@gmail.com',
    url='https://github.com/yktoo/indicator-sound-switcher',
    license='GPL3',
    package_dir={'': 'lib'},
    py_modules=['lib_pulseaudio'],
    scripts=['indicator-sound-switcher'],
    data_files=[
        ('/usr/share/applications',                      ['indicator-sound-switcher.desktop']),
        ('/usr/share/icons/ubuntu-mono-dark/status/22',  ['icons/ubuntu-mono-dark/indicator-sound-switcher.svg']),
        ('/usr/share/icons/ubuntu-mono-light/status/22', ['icons/ubuntu-mono-light/indicator-sound-switcher.svg']),
    ]
)
