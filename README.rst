catt-qt
=======

A control GUI for Chromecasts written using python3, catt api, pychromecast and PyQt5.

Features:
---------


* Able to cast files, links and playlist urls
* Control muliple chromecasts selectable from list
* Get data in real time and see changes from other devices
* Supports device reboot with initial volume setting
* Automatically plays files in same directory
* Play/Pause/Stop/Seek/Volume/Reboot
* Multi-platform

Install from PyPi:
------------------


* ``pip3 install catt pychromecast PyQt5 cattqt``

Run:
----


* ``catt-qt``
* Optionally specify ``--reconnect-volume`` with range of 0-100: ``catt-qt --reconnect-volume=25``
* By default, in the event of reconnect, the volume will be set to the volume before disconnect

Update:
-------


* ``pip3 install --no-cache-dir --upgrade cattqt``

Screenshots:
------------


.. image:: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/splashscreen.png
   :target: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/splashscreen.png
   :alt: SplashScreen


.. image:: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/x11.png
   :target: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/x11.png
   :alt: X11


.. image:: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/wayland.png
   :target: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/wayland.png
   :alt: Wayland


.. image:: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/osx.png
   :target: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/osx.png
   :alt: OSX


.. image:: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/windows.png
   :target: https://raw.githubusercontent.com/soreau/catt-qt/master/screenshots/windows.png
   :alt: Windows

