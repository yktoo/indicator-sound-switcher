sound-output-selector
=====================

Sound output selector indicator for Ubuntu/Unity. I created this very primitive app because there's just no sound output switcher indicator available in Unity.

It shows an icon in the indicator area in Ubuntu's Panel. Icon's menu allows you to switch the current sound output ('sink' in PulseAudio's terms) with just one click (okay, two clicks as first one is to get the menu open):

![Screenshot of the indicator](https://raw.github.com/yktoo/sound-output-selector/master/Screenshot.png)

It's a very initial version, although already seems to work. It completely relies on the ```pacmd``` tool to list sinks and switch audio streams between them. It does not have any change subscription capabilities, meaning, if there's an audio device added or removed, you have to manually update the list using the **Refresh device list** menu item.
