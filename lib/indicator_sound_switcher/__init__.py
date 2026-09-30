#!/usr/bin/env python3
"""
Copyright (C) 2012-2019 Dmitry Kann, http://yktoo.com

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License version 3, as published
by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranties of
MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.
---------------------------------------------------------------------------
Note for developers: some PEP8 rules are deliberately neglected here, namely:
- E211
- E221
- E241
- E272
- E402
"""

import sys
import logging
import os
import tempfile
import fcntl
import gettext

from gi.repository import GLib

from .indicator import SoundSwitcherIndicator, APP_ID, APP_NAME, APP_VERSION, DESKTOP_ID
from .config import register_portal_app_id


def _parse_cmd_line():
    """Parse command line arguments and set up logging."""
    # Check command line arguments
    lvl = logging.WARNING
    for arg in sys.argv:
        if arg == '--version':
            print('{} {}'.format(APP_NAME, APP_VERSION))
            sys.exit(0)
        elif arg == '-v':
            lvl = logging.INFO
            break
        elif arg == '-vv':
            lvl = logging.DEBUG
            break

    # Set up logging options
    logging.basicConfig(level=lvl, format='%(levelname)-8s %(message)s')


def _migrate_autostart_entry():
    """Rename the user's autostart entry from the old .desktop file name, if any. The entry typically overrides the
    system-wide one (e.g. to disable autostart), which only works if both have the same name.
    """
    autostart_dir = os.path.join(GLib.get_user_config_dir(), 'autostart')
    old_file = os.path.join(autostart_dir, APP_ID + '.desktop')
    new_file = os.path.join(autostart_dir, DESKTOP_ID + '.desktop')

    # Leave symlinks alone: they're managed by the snap launcher
    if os.path.isfile(old_file) and not os.path.islink(old_file) and not os.path.lexists(new_file):
        try:
            os.rename(old_file, new_file)
            logging.info('Renamed autostart entry %s to %s', old_file, new_file)
        except OSError as e:
            logging.warning('Failed to rename autostart entry %s: %s', old_file, e)


def main():
    """The main application routine."""
    # Set up the gettext localisation engine
    gettext.install(APP_ID)

    # Parse the command line
    _parse_cmd_line()

    # Check the indicator isn't running yet
    fd = open(os.path.join(tempfile.gettempdir(), "{}_{}.lock".format(APP_ID, os.getuid())), 'w')
    try:
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Instantiate and run the indicator
        logging.info('%s v%s', APP_NAME, APP_VERSION)
        _migrate_autostart_entry()
        register_portal_app_id(DESKTOP_ID)
        SoundSwitcherIndicator().run()

    except OSError:
        logging.info('%s is already running, exiting', APP_NAME)
