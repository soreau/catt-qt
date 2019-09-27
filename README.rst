catt-qt
=======

A control GUI for Chromecasts written using catt api, pychromecast and Qt.

Features:
---------


* Able to cast files, links and playlist urls
* Control muliple chromecasts selectable from list
* Get data in real time and shows changes from other devices
* Supports device reboot with initial volume setting
* Manage streams started by other devices
* Play/Pause/Stop/Seek/Volume/Reboot
* Multi-platform

Install:
--------


* ``pip3 install cattqt``

Run:
----


* ``catt-qt``
* Optionally specify --reconnect-volume with range of 0-100: ``catt-qt --reconnect-volume=25``
* By default, in the event of reconnect, the volume will be set to the volume before disconnect


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

