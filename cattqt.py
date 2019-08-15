"""A control GUI for Chromecasts"""

__version__ = "0.2"

# Copyright 2019 - Scott Moreau

import os
import sys
import catt.api
import subprocess
from catt.api import CattDevice
import pychromecast
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal

# On Chromecast reboot, the volume is set to maximum.
# This value is used to set a custom initial volume
# if a Chromecast is rebooted while this program is
# running. The range is 0.0 - 1.0.
REBOOT_VOLUME = 0.25


def time_to_seconds(time):
    return time.hour() * 3600 + time.minute() * 60 + time.second()


class Device:
    def __init__(self, s, d, c, i):
        self.media_listener = MediaListener()
        self.media_listener._self = s
        self.media_listener.supports_seek = False
        self.media_listener.index = i
        self.status_listener = StatusListener()
        self.status_listener._self = s
        self.status_listener.index = i
        self.connection_listener = ConnectionListener()
        self.connection_listener._self = s
        self.cast = c
        self.index = i
        self._self = s
        self.volume = 0
        self.device = d
        self.duration = 0
        self.error = ""
        self.title = ""
        self.status_text = ""
        self.live = False
        self.muted = False
        self.unmute_volume = 0
        self.paused = True
        self.playing = False
        self.stopping = False
        self.rebooting = False
        self.stopping_timer = None
        self.progress_clicked = False
        self.progress_timer = QTimer()
        self.time = QTime(0, 0, 0)
        self.progress_timer.timeout.connect(self.on_progress_tick)

    def on_progress_tick(self):
        _self = self._self
        self.time = self.time.addSecs(1)
        if (
            self.duration
            and self.duration != 0
            and time_to_seconds(self.time) >= int(self.duration)
        ):
            # If progress is at the end, stop the device progress timer
            self.set_state_idle(self.index)
            if _self.combo_box.currentIndex() == self.index:
                # If it is the currently selected device, update the ui
                self.update_ui_idle()
        if _self.combo_box.currentIndex() == self.index:
            # Update the ui elements using current progress time
            _self.progress_label.setText(self.time.toString("hh:mm:ss"))
            _self.set_progress(time_to_seconds(self.time))

    def set_state_playing(self, i, time):
        s = self._self
        hours, minutes, seconds = self.split_seconds(int(time))
        s.set_time(i, hours, minutes, seconds)
        self.paused = False
        self.playing = True
        self.error = ""
        if self.live:
            s.stop_timer.emit(i)
            self.time.setHMS(0, 0, 0)
        else:
            s.start_timer.emit(i)

    def update_ui_playing(self, time, duration):
        s = self._self
        if duration != None:
            s.progress_slider.setMaximum(duration)
        if self.live:
            self.status_text = self.title = ""
            s.skip_forward_button.setEnabled(False)
            s.progress_slider.setEnabled(False)
            s.progress_label.setText("LIVE")
            s.set_icon(s.play_button, "SP_MediaPlay")
        else:
            s.skip_forward_button.setEnabled(True)
            s.progress_slider.setEnabled(True)
            s.set_icon(s.play_button, "SP_MediaPause")
        s.set_progress(time)
        s.progress_label.setText(self.time.toString("hh:mm:ss"))
        self.update_text()

    def set_state_paused(self, i, time):
        s = self._self
        hours, minutes, seconds = self.split_seconds(int(time))
        s.set_time(i, hours, minutes, seconds)
        s.stop_timer.emit(i)
        self.paused = True
        self.playing = True
        self.error = ""

    def update_ui_paused(self, time, duration):
        s = self._self
        if duration != None:
            s.progress_slider.setMaximum(duration)
        s.set_progress(time)
        s.skip_forward_button.setEnabled(True)
        s.progress_slider.setEnabled(True)
        s.set_icon(s.play_button, "SP_MediaPlay")
        s.progress_label.setText(self.time.toString("hh:mm:ss"))
        self.update_text()

    def set_state_idle(self, i):
        s = self._self
        s.stop_timer.emit(i)
        self.time.setHMS(0, 0, 0)
        self.playing = False
        self.paused = True
        self.live = False
        self.status_text = self.title = self.error = ""

    def update_ui_idle(self):
        s = self._self
        s.set_progress(0)
        s.skip_forward_button.setEnabled(False)
        s.progress_slider.setEnabled(False)
        s.progress_label.setText(self.time.toString("hh:mm:ss"))
        s.set_icon(s.play_button, "SP_MediaPlay")
        if s.status_label.text() != "Playing..":
            self.update_text()

    def set_dial_value(self):
        s = self._self
        s.dial.valueChanged.disconnect(s.on_dial_moved)
        if self.volume != 0:
            self.unmute_volume = self.volume
        s.dial.setValue(self.volume)
        s.set_volume_label(self.volume)
        s.dial.valueChanged.connect(s.on_dial_moved)

    def split_seconds(self, s):
        hours = s // 3600
        minutes = (s - (hours * 3600)) // 60
        seconds = s - ((hours * 3600) + (minutes * 60))
        return hours, minutes, seconds

    def update_text(self):
        s = self._self
        prefix = ""
        if self.error:
            prefix = self.error
        elif self.live:
            prefix = "Streaming"
        elif not self.playing:
            if not self.stopping and not self.rebooting:
                s.status_label.setText("Idle")
            elif self.stopping:
                s.status_label.setText("Stopping..")
            elif self.rebooting:
                s.status_label.setText("Rebooting..")
            return
        elif self.paused:
            prefix = "Paused"
        if prefix and (self.status_text or self.title):
            prefix = prefix + " - "
        if self.status_text and self.title:
            if self.status_text in self.title:
                s.status_label.setText(prefix + self.title)
            elif self.title in self.status_text:
                s.status_label.setText(prefix + self.status_text)
            else:
                s.status_label.setText(prefix + self.status_text + " - " + self.title)
        elif self.status_text:
            s.status_label.setText(prefix + self.status_text)
        elif self.title:
            s.status_label.setText(prefix + self.title)
        else:
            s.status_label.setText(prefix)


class ComboBox(QComboBox):
    def __init__(self, s):
        super(ComboBox, self).__init__()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)
        self._self = s

    def showMenu(self, event):
        menu = QMenu()
        reboot_action = menu.addAction("Reboot", QComboBox)
        action = menu.exec_(self.mapToGlobal(event))
        if action == reboot_action:
            self.reboot_device()

    def reboot_device(self):
        d = self._self.stop("Rebooting..")
        print(d.device.name, "rebooting")
        self._self.play_button.setEnabled(False)
        self._self.stop_button.setEnabled(False)
        d.rebooting = True
        d.cast.reboot()


class Dial(QDial):
    def __init__(self, s):
        super(Dial, self).__init__()
        self._self = s

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._self.toggle_mute()


class App(QMainWindow):
    start_timer = pyqtSignal(int)
    stop_timer = pyqtSignal(int)
    add_device = pyqtSignal(str)
    remove_device = pyqtSignal(str)
    stopping_timer_cancel = pyqtSignal(int)

    def create_devices_layout(self):
        self.devices_layout = QHBoxLayout()
        self.combo_box = ComboBox(self)
        self.devices_layout.addWidget(self.combo_box)

    def create_control_layout(self):
        self.control_layout = QHBoxLayout()
        self.volume_layout = QVBoxLayout()
        self.dial = Dial(self)
        self.dial.setMinimum(0)
        self.dial.setMaximum(100)
        self.dial.setValue(0)
        self.dial.valueChanged.connect(self.on_dial_moved)
        self.dial.setToolTip("Volume")
        self.volume_prefix = "Vol: "
        self.volume_label = QLabel()
        self.volume_label.setText(self.volume_prefix + "0")
        self.volume_label.setAlignment(Qt.AlignCenter)
        self.volume_status_event_pending = False
        self.volume_event_timer = QTimer()
        self.volume_event_timer.timeout.connect(self.event_pending_expired)
        self.volume_event_timer.setSingleShot(True)
        self.textbox = QLineEdit()
        self.textbox.setToolTip("File, Link or Playlist")
        self.textbox.returnPressed.connect(self.on_textbox_return)
        self.play_button = QPushButton()
        self.play_button.clicked.connect(self.on_play_click)
        self.set_icon(self.play_button, "SP_MediaPlay")
        self.play_button.setToolTip("Play / Pause")
        self.stop_button = QPushButton()
        self.stop_button.clicked.connect(self.on_stop_click)
        self.set_icon(self.stop_button, "SP_MediaStop")
        self.stop_button.setToolTip("Stop")
        self.control_layout.addWidget(self.play_button)
        self.control_layout.addWidget(self.stop_button)
        self.control_layout.addWidget(self.textbox)
        self.volume_layout.addWidget(self.dial)
        self.volume_layout.addWidget(self.volume_label)
        self.control_layout.addLayout(self.volume_layout)

    def create_seek_layout(self):
        self.seek_layout = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_label.setText("00:00:00")
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setEnabled(False)
        self.progress_slider.valueChanged.connect(self.on_progress_value_changed)
        self.progress_slider.sliderPressed.connect(self.on_progress_pressed)
        self.progress_slider.sliderReleased.connect(self.on_progress_released)
        self.skip_forward_button = QPushButton()
        self.set_icon(self.skip_forward_button, "SP_MediaSkipForward")
        self.skip_forward_button.setToolTip("Skip")
        self.seek_layout.addWidget(self.progress_label)
        self.seek_layout.addWidget(self.progress_slider)
        self.seek_layout.addWidget(self.skip_forward_button)

    def create_status_layout(self):
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setText("Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_layout.addWidget(self.status_label)

    def __init__(self, app):
        super().__init__()
        self.title = "Cast All The Things"
        self.app = app
        self.width = 640
        self.height = 1
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setWindowIcon(
            QIcon(os.path.dirname(os.path.realpath(__file__)) + "/icon/chromecast.png")
        )
        self.setGeometry(640, 480, self.width, self.height)
        print("Scanning for Chromecast devices on the network...")
        self.devices = catt.api.discover()
        num_devices = len(self.devices)
        if num_devices == 0:
            print("No devices found")
            sys.exit(1)
        self.window = QWidget()
        self.main_layout = QVBoxLayout()
        self.create_devices_layout()
        self.create_control_layout()
        self.create_seek_layout()
        self.create_status_layout()
        self.skip_forward_button.setEnabled(False)
        self.skip_forward_button.clicked.connect(self.on_skip_click)
        self.start_timer.connect(self.on_start_timer)
        self.stop_timer.connect(self.on_stop_timer)
        self.add_device.connect(self.on_add_device)
        self.remove_device.connect(self.on_remove_device)
        self.stopping_timer_cancel.connect(self.on_stopping_timer_cancel)
        self.textbox_return = False
        self.device_list = []
        if num_devices > 1:
            text = "devices found"
        else:
            text = "device found"
        print(num_devices, text)
        i = 0
        for d in self.devices:
            cast = pychromecast.Chromecast(d.ip_addr)
            cast.wait()
            device = Device(self, d, cast, i)
            cast.media_controller.register_status_listener(device.media_listener)
            cast.register_status_listener(device.status_listener)
            cast.register_connection_listener(device.connection_listener)
            self.device_list.append(device)
            self.combo_box.addItem(d.name)
            # Hack: Change volume slightly to trigger
            # status listener. This way, we can get the
            # volume on startup.
            d.volumedown(0.0000001)
            print(d.name)
            i = i + 1
        self.combo_box.currentIndexChanged.connect(self.on_index_changed)
        self.main_layout.addLayout(self.devices_layout)
        self.main_layout.addLayout(self.control_layout)
        self.main_layout.addLayout(self.seek_layout)
        self.main_layout.addLayout(self.status_layout)
        self.main_layout.addStretch()
        self.widget = QWidget()
        self.widget.setLayout(self.main_layout)
        self.setCentralWidget(self.widget)
        self.show()

    def play(self, d, text):
        if text == "" or (
            not "://" in text and not ":\\" in text and not text.startswith("/")
        ):
            return
        self.status_label.setText("Playing..")
        subprocess.Popen(["catt", "-d", d.device.name, "cast", text])

    def on_play_click(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.error = ""
        if d.paused or d.live:
            if d.playing and not d.live:
                d.device.play()
                self.set_icon(self.play_button, "SP_MediaPause")
                d.paused = False
                return
            self.play(d, self.textbox.text())
        elif d.playing:
            if self.textbox_return:
                self.textbox_return = False
                self.play(d, self.textbox.text())
                return
            self.set_icon(self.play_button, "SP_MediaPlay")
            d.device.pause()
            d.paused = True
            d.progress_timer.stop()

    def on_textbox_return(self):
        self.textbox_return = True
        self.on_play_click()

    def on_stopping_timer_cancel(self, i):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.stopping_timer.stop()
        d.stopping_timer = None

    def on_stopping_timeout(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.stopping = False
        d.update_text()

    def stop(self, text):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.set_state_idle(i)
        self.status_label.setText(text)
        d.update_ui_idle()
        return d

    def on_stop_click(self):
        d = self.stop("Stopping..")
        d.stopping_timer = QTimer.singleShot(3000, self.on_stopping_timeout)
        self.play_button.setEnabled(True)
        d.stopping = True
        d.device.stop()

    def on_index_changed(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        if d.playing and not d.paused and not d.live:
            self.set_icon(self.play_button, "SP_MediaPause")
        else:
            self.set_icon(self.play_button, "SP_MediaPlay")
        enabled = d.playing and not d.live
        self.skip_forward_button.setEnabled(enabled)
        self.progress_slider.setEnabled(enabled)
        if d.duration != None:
            self.progress_slider.setMaximum(d.duration)
        self.set_progress(time_to_seconds(d.time))
        if d.live:
            self.play_button.setEnabled(True)
            self.progress_label.setText("LIVE")
            self.stop_timer.emit(d.index)
            d.time.setHMS(0, 0, 0)
        else:
            self.progress_label.setText(d.time.toString("hh:mm:ss"))
            enabled = not d.rebooting
            self.play_button.setEnabled(enabled)
            self.stop_button.setEnabled(enabled)
        d.set_dial_value()
        d.update_text()

    def on_skip_click(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.device.seek(d.duration - 3)

    def on_dial_moved(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        if not self.volume_status_event_pending:
            self.volume_status_event_pending = True
            d.device.volume(self.dial.value() / 100)
            self.volume_event_timer.start(250)
        elif self.dial.value() == 0:
            d.device.volume(0.0)
            self.set_volume_label(0)
        elif self.dial.value() == 100:
            d.device.volume(1.0)
            self.set_volume_label(100)

    def toggle_mute(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        if d.muted:
            d.device.volume(d.unmute_volume / 100)
            d.muted = False
        else:
            d.unmute_volume = d.volume
            d.device.volume(0.0)
            d.muted = True

    def seek(self, d, value):
        self.status_label.setText("Seeking..")
        d.device.seek(value)

    def on_progress_value_changed(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d.progress_clicked:
            return
        if d.media_listener.supports_seek:
            v = int(self.progress_slider.value())
            self.stop_timer.emit(i)
            if v != int(d.duration):
                self.seek(d, v)

    def on_progress_pressed(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.progress_timer.stop()
        d.progress_clicked = True
        self.current_progress = self.progress_slider.value()

    def on_progress_released(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        value = self.progress_slider.value()
        d.progress_clicked = False
        if d.media_listener.supports_seek:
            if value > self.current_progress or value < self.current_progress:
                self.seek(d, value)
        else:
            print("Stream does not support seeking")

    def on_start_timer(self, i):
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.progress_timer.start(1000)

    def on_stop_timer(self, i):
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.progress_timer.stop()

    def set_time(self, i, h, m, s):
        d = self.get_device_from_index(i)
        if d == None:
            return
        d.time.setHMS(h, m, s)

    def set_icon(self, button, icon):
        button.setIcon(self.app.style().standardIcon(getattr(QStyle, icon)))

    def event_pending_expired(self):
        self.volume_status_event_pending = False

    def on_add_device(self, ip):
        for d in self.device_list:
            if d.device.ip_addr == ip:
                self.devices.remove(d.device)
                self.device_list.remove(d)
                break
        d = CattDevice(ip_addr=ip)
        d._cast.wait()
        device = Device(self, d, d._cast, self.combo_box.count())
        d._cast.media_controller.register_status_listener(device.media_listener)
        d._cast.register_status_listener(device.status_listener)
        self.devices.append(d)
        self.device_list.append(device)
        self.combo_box.addItem(d.name)
        if self.combo_box.currentIndex() == device.index:
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        self.set_volume_label(REBOOT_VOLUME * 100)
        d.volume(REBOOT_VOLUME)

    def on_remove_device(self, ip):
        d = self.get_device_from_ip(ip)
        if d == None:
            return
        try:
            d.cast.media_controller._status_listeners.remove(d.media_listener)
        except Exception as e:
            print(ip, "Unregistering media controller failed:", e)
        try:
            d.cast.socket_client.receiver_controller._status_listeners.remove(
                d.status_listener
            )
        except Exception as e:
            print(ip, "Unregistering status listener failed:", e)
        self.stop_timer.emit(d.index)
        d.time.setHMS(0, 0, 0)
        d.playing = False
        d.paused = True
        d.live = False
        self.combo_box.clear()
        i = 0
        j = 0
        devices_active = False
        lost_devices = ""
        for _d in self.device_list:
            if d == _d or _d.index == -1:
                _d.media_listener.index = _d.status_listener.index = _d.index = -1
                if j == len(self.device_list) - 1:
                    lost_devices = lost_devices + " and "
                elif j != 0:
                    lost_devices = lost_devices + ", "
                lost_devices = lost_devices + "'" + _d.device.name + "'"
            else:
                self.combo_box.addItem(_d.device.name)
                _d.media_listener.index = _d.status_listener.index = _d.index = i
                if i == 0:
                    _d.update_text()
                i = i + 1
                devices_active = True
            j = j + 1
        self.on_index_changed()
        if not devices_active:
            self.status_label.setText("Listening for " + lost_devices)

    def get_device_from_ip(self, ip):
        for d in self.device_list:
            if d.device.ip_addr == ip:
                return d
        return None

    def get_device_from_index(self, i):
        for d in self.device_list:
            if d.index == i:
                return d
        return None

    def set_progress(self, v):
        try:
            self.progress_slider.valueChanged.disconnect(self.on_progress_value_changed)
        except:
            pass
        self.progress_slider.setValue(v)
        try:
            self.progress_slider.valueChanged.connect(self.on_progress_value_changed)
        except:
            pass

    def set_volume_label(self, v):
        self.volume_label.setText(self.volume_prefix + str(round(v)))


class MediaListener:
    def new_media_status(self, status):
        s = self._self
        i = s.combo_box.currentIndex()
        index = self.index
        if index == -1:
            return
        self.supports_seek = status.supports_seek
        if i != index:
            d = s.get_device_from_index(index)
            if d == None:
                return
            d.duration = status.duration
            d.title = status.title
            d.stopping = False
            d.rebooting = False
            if status.player_state == "PLAYING":
                d.live = status.stream_type == "LIVE"
                d.set_state_playing(index, status.current_time)
            elif status.player_state == "PAUSED":
                d.set_state_paused(index, status.current_time)
            elif status.player_state == "IDLE" or status.player_state == "UNKNOWN":
                d.set_state_idle(index)
            return
        d = s.get_device_from_index(i)
        if d == None:
            return
        d.duration = status.duration
        d.title = status.title
        d.stopping = False
        d.rebooting = False
        if d.stopping_timer:
            s.stopping_timer_cancel.emit(i)
        if status.player_state == "PLAYING":
            d.live = status.stream_type == "LIVE"
            d.set_state_playing(i, status.current_time)
            d.update_ui_playing(status.current_time, status.duration)
        elif status.player_state == "PAUSED":
            d.set_state_paused(i, status.current_time)
            d.update_ui_paused(status.current_time, status.duration)
        elif status.player_state == "IDLE" or status.player_state == "UNKNOWN":
            d.set_state_idle(i)
            d.update_ui_idle()


class StatusListener:
    def new_cast_status(self, status):
        s = self._self
        i = s.combo_box.currentIndex()
        index = self.index
        if index == -1:
            return
        v = status.volume_level * 100
        d = s.get_device_from_index(index)
        if d == None:
            return
        if i != index:
            d.volume = v
            d.status_text = status.status_text
            return
        d = s.get_device_from_index(i)
        if d == None:
            return
        d.volume = v
        d.status_text = status.status_text
        if not s.volume_status_event_pending:
            d.set_dial_value()
        else:
            s.set_volume_label(d.volume)
            if d.volume > 0:
                d.muted = False
        s.volume_status_event_pending = False


class ConnectionListener:
    def new_connection_status(self, status):
        _self = self._self
        if status.status == "CONNECTED":
            print(status.address.address, "connected")
            _self.add_device.emit(status.address.address)
        elif status.status == "LOST":
            print(status.address.address, "disconnected")
            _self.remove_device.emit(status.address.address)


def main():
    app = QApplication(sys.argv)
    ex = App(app)
    sys.exit(app.exec_())
