Sound Switcher Indicator
========================

Sound input/output selector indicator for Ubuntu/Unity. I created this app because there was just no sound switcher indicator available.

It shows an icon in the indicator area in Ubuntu's Panel. The icon's menu allows you to switch the current sound input and output (i.e. *source ports* and *sink ports* in PulseAudio's terms, respectively) with just two clicks:

![Screenshot of the indicator](Screenshot.png)

The application makes use of the native PulseAudio API (version 4.0 or newer is required).


Installation
------------

Please refer to the [INSTALL](INSTALL) document.

For details see http://yktoo.com/software/indicator-sound-switcher


Bug Reporting
-------------

Run the application in verbose mode to see the detailed log:

    indicator-sound-switcher -vv

and, once the error condition has been reproduced, attach the output to the report.
