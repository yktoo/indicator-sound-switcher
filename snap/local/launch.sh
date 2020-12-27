#!/bin/sh

# Make sure a link to desktop launcher is added to the autostart dir
autostart_dir="$SNAP_USER_DATA/.config/autostart"
if [ ! -d "$autostart_dir" ]; then
	mkdir -p "$autostart_dir"
	ln -sfnt "$autostart_dir/" "$SNAP/share/applications/indicator-sound-switcher.desktop"
fi

exec "$@"
