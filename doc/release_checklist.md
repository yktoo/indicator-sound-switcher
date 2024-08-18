# Release checklist

## Prerequisites

```bash
sudo apt-get install -y devscripts debhelper dh-python
```

### Snaps

If you intend to build snaps locally:

```bash
sudo snap install snapcraft --classic
sudo snap install multipass
```

Log into Snapcraft with your Ubuntu One account:

```bash
snapcraft login
```

## Making a release

1. Update app version in the header of ./setup.py
2. Add change info into ./debian/changelog (`dch -v <VERSION>-1`)
3. Run ./build_package to build a source tarball and the accompanying files
4. Run the dput command displayed by build_package
5. Create snap: snapcraft clean && snapcraft snap
6. Upload snap: snapcraft upload --release=stable indicator-sound-switcher*.snap
