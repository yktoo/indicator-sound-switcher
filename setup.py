#!/usr/bin/env python3

from distutils.core import setup
import os
import shutil


PO_DIR      = 'po'
LOCALE_DIR  = 'locale'
APP_ID      = 'indicator-sound-switcher'
APP_VERSION = '2.2.2'


def compile_lang_files() -> list:
    """(Re)generate .mo files from the available .po files, if any
    :return: list of .mo files to be packaged or installed
    """
    # Get a canonical locale path
    locale_dir = os.path.abspath(LOCALE_DIR)

    # Get a canonical path to the .po dir
    po_dir = os.path.abspath(PO_DIR)

    # Installing/packaging from the source tree (the 'po' dir is available): compile .po into .mo
    if os.path.isdir(po_dir):
        # Remove the locale dir altogether, if any
        if os.path.isdir(locale_dir):
            shutil.rmtree(locale_dir)
        # Create a new dir
        os.makedirs(locale_dir)
        # Iterate through available .po files
        for in_file in os.listdir(po_dir):
            if in_file.endswith('.po'):
                # Use the name of .po file (without extension) as the language name
                lang = os.path.splitext(in_file)[0]
                # Create a target dir for the .mo file
                mo_dir = os.path.join(locale_dir, lang, 'LC_MESSAGES')
                os.makedirs(mo_dir)
                # Compile the .po into a .mo
                print('INFO: Compiling {} into {}/{}.mo'.format(in_file, mo_dir, APP_ID))
                os.system(
                    'msgfmt "{}" -o "{}"'.format(os.path.join(po_dir, in_file), os.path.join(mo_dir, APP_ID + '.mo')))
    else:
        print('WARNING: Directory {} doesn\'t exist, no .po locale files available'.format(po_dir))

    # Check the locale dir is there
    if not os.path.isdir(locale_dir):
        print('WARNING: Directory {} doesn\'t exist, no locale files will be included'.format(locale_dir))
        return []

    # Return all available .mo translation files to the list data files
    return [
        (
            'share/locale/{}/LC_MESSAGES'.format(lang),
            [os.path.join(LOCALE_DIR, lang, 'LC_MESSAGES', APP_ID + '.mo')]
        ) for lang in os.listdir(locale_dir)
    ]


data_files = [
    # App shortcut
    ('share/applications',                      [APP_ID+'.desktop']),

    # Autostart entry
    ('/etc/xdg/autostart',                      [APP_ID+'.desktop']),

    # Icons
    ('share/icons/ubuntu-mono-dark/status/22',  ['icons/ubuntu-mono-dark/indicator-sound-switcher.svg']),
    ('share/icons/ubuntu-mono-light/status/22', ['icons/ubuntu-mono-light/indicator-sound-switcher.svg']),
    ('share/icons/hicolor/22x22/status',        ['icons/default/indicator-sound-switcher.svg']),
    ('share/icons/hicolor/scalable/status',     ['icons/default/indicator-sound-switcher.svg']),

    # Manpage
    ('share/man/man1',                          ['man/indicator-sound-switcher.1']),
]

# Configure
setup(
    name=APP_ID,
    version=APP_VERSION,
    description='Sound input/output selector indicator',
    author='Dmitry Kann',
    author_email='yktooo@gmail.com',
    url='https://github.com/yktoo/indicator-sound-switcher',
    license='GPL3',
    package_dir={'': 'lib'},
    packages=['indicator_sound_switcher'],
    package_data={'indicator_sound_switcher': ['*.glade']},
    scripts=['indicator-sound-switcher'],
    data_files=data_files + compile_lang_files(),
)
