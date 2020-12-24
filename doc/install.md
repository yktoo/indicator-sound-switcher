# Sound Switcher Indicator: Installation

## Installation from the PPA (recommended)

If you're on Ubuntu or one of it's derivatives, it's always advisable to use the standard package distribution mechanism (Private Package Archive, PPA). This way you'll automatically get updated indicator versions in the future.

In order to install the application from [my PPA](https://launchpad.net/~yktooo/+archive/ubuntu/ppa):

    sudo apt-add-repository ppa:yktooo/ppa
    sudo apt-get update
    sudo apt-get install indicator-sound-switcher


## Installation using a binary package

If you don't want or can't install from the PPA, you can download and install the `.deb` binary package manually.

1. Go to the [Packages](https://launchpad.net/~yktooo/+archive/ubuntu/ppa/+packages) Launchpad page.
2. Choose the right (perhaps latest) version of the `indicator-sound-switcher` package and click to expand it.
3. Download the `indicator-sound-switcher_<VERSION>_all.deb` file.
4. Install the downloaded `.deb` using the Software Center or with the command:
    <pre>sudo dpkg -i /path/to/downloaded/indicator-sound-switcher_*_all.deb</pre>


## Installation from the source tarball

In order to install the application from the source tarball:

1. Make sure the required dependencies are installed (you can replace `gir1.2-ayatanaappindicator3-0.1` with `gir1.2-appindicator3-0.1` if the former isn't available in your distro):
```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 gir1.2-keybinder-3.0
```
2. Download the tarball (`indicator-sound-switcher-*.tar.gz`)
3. Decompress the archive: `tar xf indicator-sound-switcher-*.tar.gz`
4. `cd` to the `indicator-sound-switcher-*` dir
5. Run `sudo python3 setup.py install`
