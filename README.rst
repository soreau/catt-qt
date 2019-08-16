**catt-qt** is a control GUI for Chromecasts.

catt-qt
=======

Cast All The Things Qt GUI

Written using catt api and pychromecast

Features:


* Able to cast files, links and playlist urls
* Control muliple chromecasts selectable from list
* Get data in real time and shows changes from other devices
* Supports device reboot with initial volume setting
* Manage streams started by other devices
* Play/Pause/Stop/Seek/Volume/Reboot
* Multi-platform

Limitations:


* Takes about 8 seconds to scan for chromecasts when started
* Services that require login or complicated clicks in browser to play need to be started from a browser or other device

Install:


* ``pip3 install cattqt`` will install from `pypi <https://pypi.org/project/cattqt/>`_

Run:


* ``catt-qt``
* Optionally specify --reboot-volume with range of 0-100: ``catt-qt --reboot-volume=25``


.. image:: https://github.com/soreau/catt-qt/blob/master/screenshots/x11.png
   :target: https://github.com/soreau/catt-qt/blob/master/screenshots/x11.png
   :alt: X11


.. image:: https://github.com/soreau/catt-qt/blob/master/screenshots/wayland.png
   :target: https://github.com/soreau/catt-qt/blob/master/screenshots/wayland.png
   :alt: Wayland


.. image:: https://github.com/soreau/catt-qt/blob/master/screenshots/osx.png
   :target: https://github.com/soreau/catt-qt/blob/master/screenshots/osx.png
   :alt: OSX


.. image:: https://github.com/soreau/catt-qt/blob/master/screenshots/windows.png
   :target: https://github.com/soreau/catt-qt/blob/master/screenshots/windows.png
   :alt: Windows

