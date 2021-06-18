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

NB: there's a [known issue](https://github.com/canonical/multipass/issues/1866) in Multipass when it cannot reach the network if Docker is installed on the machine, use the following script to resolve that:

```bash
#!/bin/bash

for table in filter nat mangle; do
  sudo iptables-legacy -t $table -S | grep Multipass | xargs -L1 sudo iptables-nft -t $table
done
```

## Making a release

1. Update app version in the header of ./setup.py
2. Add change info into ./debian/changelog
3. Run ./build_package to build a source tarball and the accompanying files
4. Run the dput command displayed by build_package
5. Create snap: snapcraft clean && snapcraft snap
6. Upload snap: snapcraft upload --release=stable indicator-sound-switcher*.snap
