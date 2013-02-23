indicator-sound-switcher
========================

Sound input/output selector indicator for Ubuntu/Unity. I created this app because there was just no sound switcher indicator available.

It shows an icon in the indicator area in Ubuntu's Panel. Icon's menu allows you to switch the current sound input and output ('source' and 'sink' in PulseAudio's terms, respectively) with just two clicks:

![Screenshot of the indicator](https://raw.github.com/yktoo/indicator-sound-switcher/master/Screenshot.png)

The application makes use of native PulseAudio interface and appropriate Python bindings (```lib_pulseaudio```). The list of devices is updated automatically thanks to PulseAudio subscription capabilities.

Installation
------------

To install ```lib_pulseaudio``` use:

```sudo pip install libpulseaudio```

In order to make icon available, you need to create a symlink in ```/usr/share/pixmaps```:

```sudo ln -s /path/to/app/indicator_sound_switcher.svg /usr/share/pixmaps/indicator_sound_switcher.svg```

After that simply start ```indicator-sound-switcher```
