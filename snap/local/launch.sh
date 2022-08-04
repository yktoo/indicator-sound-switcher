#!/bin/sh

# Make sure a link to desktop launcher is added to the autostart dir

AUTOSTART="$SNAP_USER_DATA/.config/autostart"

if [ ! -d "$AUTOSTART" ]; then
    mkdir -p "$AUTOSTART"
fi

ln -sfnt "$AUTOSTART/" "$SNAP/share/applications/indicator-sound-switcher.desktop"

exec "$@"
