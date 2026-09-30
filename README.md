[![GitHub release](https://img.shields.io/github/v/release/yktoo/indicator-sound-switcher.svg)](https://github.com/yktoo/indicator-sound-switcher/releases/latest)
[![GitHub](https://img.shields.io/github/license/yktoo/indicator-sound-switcher.svg)](COPYING)

# Sound Switcher Indicator

Sound input/output selector application for Linux.

It shows an icon in the indicator area or the system tray (whatever is available in your desktop environment). The icon's menu allows you to switch the current sound input and output (i.e. *source ports* and *sink ports* in PulseAudio's terms, respectively) with just two clicks:

![Screenshot of the indicator](doc/menu.png)

The application makes use of the native PulseAudio API.

For details see:
* http://yktoo.com/en/software/indicator-sound-switcher/ (English)
* http://yktoo.com/ru/software/indicator-sound-switcher/ (русский)

More in the documentation:
* [Installation](doc/install.md)
* [Configuration](doc/config.md)
* [Localisation](doc/i18n.md)
* [Changelog](debian/changelog)


## Why libayatana-appindicator (and not libayatana-appindicator-glib)

The application uses the GTK 3 `libayatana-appindicator3` library (falling back to the older `libappindicator3`) to display its icon and menu. `libayatana-appindicator3` is officially deprecated in favour of `libayatana-appindicator-glib`, however the latter exports the indicator menu only via the `org.gtk.Menus` D-Bus interface, whereas most tray hosts — including GNOME Shell's AppIndicator extension and KDE Plasma — expect the `com.canonical.dbusmenu` interface. With `libayatana-appindicator-glib` the icon would still appear, but its menu wouldn't work on those desktops.

The application therefore sticks to `libayatana-appindicator3` for the time being.


## Bug Reporting

Run the application in verbose mode to see the detailed log:

    indicator-sound-switcher -vv

and, once the error condition has been reproduced, [file a bug report](https://github.com/yktoo/indicator-sound-switcher/issues) and attach the output to it.
