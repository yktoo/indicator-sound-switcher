# Sound Switcher Indicator: Installation

## Installation from PPA (recommended)

It's always advisable to use the standard Ubuntu package distribution mechanism (PPA). To install the application from my PPA:

    sudo apt-add-repository ppa:yktooo/ppa
    sudo apt-get update
    sudo apt-get install indicator-sound-switcher


## Installation from the source tarball

In order to install the application from the source tarball:

1. Download the tarball (`indicator-sound-switcher-*.tar.gz`)
2. Decompress the archive: `tar xf indicator-sound-switcher-*.tar.gz`
3. `cd` to the `indicator-sound-switcher-*` dir
4. Run `sudo python3 setup.py install`
