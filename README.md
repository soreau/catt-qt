# catt-qt
Cast All The Things Qt GUI

Written using catt api and pychromecast

Features:
- Able to cast files, links and playlist urls
- Control muliple chromecasts selectable from list
- Get data in real time and shows changes from other devices
- Supports device reboot with initial volume setting
- Manage streams started by other devices
- Play/Pause/Stop/Seek/Volume/Reboot

Limitations:
- Takes about 8 seconds to scan for chromecasts when started
- Requires [this pychromecast patch](https://github.com/balloob/pychromecast/commit/15655117236b4d856677d5c58a0a29883665003a) for detecting reboots properly
- Services that require login or complicated clicks in browser to play need to be started from a browser or other device

Usage:
- Install [catt](https://github.com/skorokithakis/catt) and [pychromecast](https://github.com/balloob/pychromecast) with pip3
- Install PyQt5
- Install git and clone catt-qt
- Run ./catt-qt.py from the repository directory

![X11](https://github.com/soreau/catt-qt/blob/master/screenshots/x11.png "X11")
![Wayland](https://github.com/soreau/catt-qt/blob/master/screenshots/wayland.png "Wayland")
![OSX](https://github.com/soreau/catt-qt/blob/master/screenshots/osx.png "OSX")
![Windows](https://github.com/soreau/catt-qt/blob/master/screenshots/windows.png "Windows")
