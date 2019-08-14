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
- Requires [this pychromecast patch](https://github.com/balloob/pychromecast/pull/305) for detecting reboots properly

Usage:
- Install [catt](https://github.com/skorokithakis/catt) and [pychromecast](https://github.com/balloob/pychromecast) with pip3
- Install git and clone catt-qt
- Run ./catt-qt.py from the repository directory

![alt text](https://github.com/soreau/catt-qt/blob/master/screenshot.png "catt-qt")
