#!/bin/sh

# Make sure a link to desktop launcher is added to the autostart dir

AUTOSTART="$SNAP_USER_DATA/.config/autostart/"

mkdir -p "$AUTOSTART"

ln -sfnt "$AUTOSTART" "$SNAP/share/applications/com.yktoo.IndicatorSoundSwitcher.desktop"

# Remove the link created by older versions, which used a different desktop file name
rm -f "$AUTOSTART/indicator-sound-switcher.desktop"

exec "$@"
