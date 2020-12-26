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

from .indicator import SoundSwitcherIndicator, APP_ID


def _parse_cmd_line():
    """Parse command line arguments. Currently only sets up logging."""
    # Check command line arguments
    lvl = logging.WARNING
    for arg in sys.argv:
        if arg == '-v':
            lvl = logging.INFO
            break
        elif arg == '-vv':
            lvl = logging.DEBUG
            break

    # Set up logging options
    logging.basicConfig(level=lvl, format='%(levelname)-8s %(message)s')


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
        logging.info('Starting indicator application')
        SoundSwitcherIndicator().run()

    except OSError:
        logging.info('Indicator is already running, exiting')
