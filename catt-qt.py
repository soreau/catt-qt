#!/usr/bin/python3

# Copyright 2019 - Scott Moreau

import sys
import catt.api
import pychromecast
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal


def time_to_seconds(time):
	return time.hour() * 3600 + time.minute() * 60 + time.second()

class Device:
	def __init__(self = None, s = None, d = None, i = 0):
		self.media_listener = MediaListener()
		self.media_listener._self = s
		self.media_listener.supports_seek = False
		self.media_listener.index = i
		self.status_listener = StatusListener()
		self.status_listener._self = s
		self.status_listener.index = i
		self.index = i
		self._self = s
		self.volume = 0
		self.paused = False
		self.playing = False
		self.device = d
		self.duration = 0
		self.status_text = None
		self.progress_timer = QTimer()
		self.time = QTime(0, 0, 0)
		self.progress_timer.timeout.connect(self.on_progress_tick)

	def on_progress_tick(self):
		_self = self._self
		self.time = self.time.addSecs(1)
		if _self.combo_box.currentIndex() == self.index:
			_self.progress_label.setText(self.time.toString("hh:mm:ss"))
			_self.progress_slider.setValue(time_to_seconds(self.time))

class App(QMainWindow):
	start_timer = pyqtSignal(int)
	stop_timer = pyqtSignal(int)

	def __init__(self):
		super().__init__()
		self.title = 'Cast All The Things'
		self.width = 640
		self.height = 1
		self.initUI()

	def initUI(self):
		self.setWindowTitle(self.title)
		self.setGeometry(640, 480, self.width, self.height)
		print('Scanning for Chromecast devices on the network...')
		self.devices = catt.api.discover()
		if len(self.devices) == 0:
			print('No devices found')
			sys.exit(1)
		self.combo_box = QComboBox()
		self.combo_box.currentIndexChanged.connect(self.on_index_changed)
		self.paused = True
		self.window = QWidget()
		self.main_layout = QVBoxLayout()
		self.devices_layout = QHBoxLayout()
		self.control_layout = QHBoxLayout()
		self.seek_layout = QHBoxLayout()
		self.status_layout = QHBoxLayout()
		self.play_button = QPushButton()
		self.stop_button = QPushButton()
		self.skip_forward_button = QPushButton()
		self.textbox = QLineEdit()
		self.dial = QDial()
		self.dial.setMinimum(0)
		self.dial.setMaximum(100)
		self.dial.setValue(0)
		self.dial.valueChanged.connect(self.on_dial_moved)
		self.dial.sliderPressed.connect(self.on_dial_pressed)
		self.dial.sliderReleased.connect(self.on_dial_released)
		self.dial_pressed = False
		self.dial_value = 0.0
		self.dial_user_modified = False
		self.progress_label = QLabel()
		self.progress_label.setText('00:00:00')
		self.progress_slider = QSlider(Qt.Horizontal)
		self.progress_slider.setValue(0)
		self.progress_slider.setEnabled(False)
		self.progress_slider.sliderPressed.connect(self.on_progress_pressed)
		self.progress_slider.sliderReleased.connect(self.on_progress_released)
		self.status_label = QLabel()
		self.status_label.setText('Idle')
		self.status_label.setAlignment(Qt.AlignCenter)
		self.current_progress = 0
		self.play_button.setIcon(app.style().standardIcon(getattr(QStyle, 'SP_MediaPlay')))
		self.stop_button.setIcon(app.style().standardIcon(getattr(QStyle, 'SP_MediaStop')))
		self.skip_forward_button.setIcon(app.style().standardIcon(getattr(QStyle, 'SP_MediaSkipForward')))
		self.skip_forward_button.setEnabled(False)
		self.play_button.clicked.connect(self.on_play_click)
		self.stop_button.clicked.connect(self.on_stop_click)
		self.skip_forward_button.clicked.connect(self.on_skip_click)
		self.start_timer.connect(self.on_start_timer)
		self.stop_timer.connect(self.on_stop_timer)
		self.device_list = []
		print(len(self.devices), 'devices found')
		i = 0
		for d in self.devices:
			cast = pychromecast.Chromecast(d.ip_addr)
			cast.wait()
			device = Device(self, d, i)
			cast.media_controller.register_status_listener(device.media_listener)
			cast.register_status_listener(device.status_listener)
			self.device_list.append(device)
			self.combo_box.addItem(d.name)
			# Hack: Change volume slightly to trigger
			# status listener. This way, we can get the
			# volume on startup.
			d.volumedown(0.0000001)
			print(d.name)
			i = i + 1
		self.devices_layout.addWidget(self.combo_box)
		self.control_layout.addWidget(self.play_button)
		self.control_layout.addWidget(self.stop_button)
		self.control_layout.addWidget(self.textbox)
		self.control_layout.addWidget(self.dial)
		self.seek_layout.addWidget(self.progress_label)
		self.seek_layout.addWidget(self.progress_slider)
		self.seek_layout.addWidget(self.skip_forward_button)
		self.status_layout.addWidget(self.status_label)
		self.main_layout.addLayout(self.devices_layout)
		self.main_layout.addLayout(self.control_layout)
		self.main_layout.addLayout(self.seek_layout)
		self.main_layout.addLayout(self.status_layout)
		self.widget = QWidget()
		self.widget.setLayout(self.main_layout)
		self.setCentralWidget(self.widget)
		self.show()

	def on_play_click(self):
		i = self.combo_box.currentIndex()
		if (self.play_button.icon().name() == 'media-playback-start'):
			if self.device_list[i].paused:
				self.devices[i].play()
				self.set_pause_icon()
				self.device_list[i].paused = False
				return
			text = self.textbox.text()
			if "://" in text:
				self.set_pause_icon()
				self.devices[i].play_url(text, resolve=True, block=False)
		elif (self.play_button.icon().name() == 'media-playback-pause'):
			self.set_play_icon()
			self.devices[i].pause()
			self.device_list[i].paused = True

	def on_stop_click(self):
		i = self.combo_box.currentIndex()
		self.devices[i].stop()
		self.stop_timer.emit(i)
		self.device_list[i].time = QTime(0, 0, 0)
		self.progress_slider.setValue(0)
		self.progress_label.setText(self.device_list[i].time.toString("hh:mm:ss"))
		self.set_play_icon()
		self.skip_forward_button.setEnabled(False)
		self.progress_slider.setEnabled(False)
		self.device_list[i].playing = False

	def on_index_changed(self):
		i = self.combo_box.currentIndex()
		if self.device_list[i].playing:
			self.set_pause_icon()
		else:
			self.set_play_icon()
		self.skip_forward_button.setEnabled(self.device_list[i].playing)
		self.progress_slider.setEnabled(self.device_list[i].playing)
		self.progress_label.setText(self.device_list[i].time.toString("hh:mm:ss"))
		self.progress_slider.setMaximum(self.device_list[i].duration)
		self.progress_slider.setValue(time_to_seconds(self.device_list[i].time))
		self.dial.valueChanged.disconnect(self.on_dial_moved)
		self.dial.setValue(self.device_list[i].volume)
		self.dial.valueChanged.connect(self.on_dial_moved)
		self.status_label.setText(self.device_list[i].status_text)

	def on_skip_click(self):
		i = self.combo_box.currentIndex()
		self.devices[i].seek(self.device_list[i].duration - 3)

	def on_dial_moved(self):
		i = self.combo_box.currentIndex()
		self.devices[i].volume(self.dial.value() / 100)

	def on_dial_pressed(self):
		self.dial_user_modified = True

	def on_dial_released(self):
		self.dial_value = self.dial.value()

	def on_progress_pressed(self):
		self.device_list[self.combo_box.currentIndex()].progress_timer.stop()
		self.current_progress = self.progress_slider.value()

	def on_progress_released(self):
		i = self.combo_box.currentIndex()
		value = self.progress_slider.value()
		if self.device_list[i].media_listener.supports_seek:
			if value > self.current_progress:
				self.devices[i].seek(value)
			elif value < self.current_progress:
				self.devices[i].seek(value)
		else:
			print('Stream does not support seeking')

	def on_start_timer(self, i):
		self.device_list[i].progress_timer.start(1000)

	def on_stop_timer(self, i):
		self.device_list[i].progress_timer.stop()
		self.device_list[i].time.setHMS(0, 0, 0)

	def set_time(self, i, h, m, s):
		self.device_list[i].time.setHMS(h, m, s)

	def set_play_icon(self):
		self.play_button.setIcon(app.style().standardIcon(getattr(QStyle, 'SP_MediaPlay')))

	def set_pause_icon(self):
		self.play_button.setIcon(app.style().standardIcon(getattr(QStyle, 'SP_MediaPause')))

class MediaListener:
	def new_media_status(self, status):
		_self = self._self
		i = _self.combo_box.currentIndex()
		index = self.index
		self.supports_seek = status.supports_seek
		if i != index:
			if (status.player_state == 'PLAYING'):
				_self.device_list[index].duration = status.duration
				hours, minutes, seconds = self.split_seconds(int(status.current_time))
				_self.set_time(index, hours, minutes, seconds)
				_self.start_timer.emit(index)
				_self.device_list[index].playing = True
			elif ((status.player_state == 'IDLE' or status.player_state == 'UNKNOWN') and status.idle_reason == 'FINISHED'):
				_self.stop_timer.emit(index)
				_self.device_list[index].time = QTime(0, 0, 0)
				_self.device_list[index].playing = False
			return
		if (status.player_state == 'PLAYING'):
			_self.device_list[i].duration = status.duration
			_self.progress_slider.setMaximum(status.duration)
			_self.progress_slider.setValue(status.current_time)
			hours, minutes, seconds = self.split_seconds(int(status.current_time))
			_self.set_time(i, hours, minutes, seconds)
			_self.start_timer.emit(i)
			_self.skip_forward_button.setEnabled(True)
			_self.progress_slider.setEnabled(True)
			_self.device_list[i].playing = True
			_self.progress_label.setText(_self.device_list[i].time.toString("hh:mm:ss"))
		elif ((status.player_state == 'IDLE' or status.player_state == 'UNKNOWN') and status.idle_reason == 'FINISHED'):
			_self.set_play_icon()
			_self.skip_forward_button.setEnabled(False)
			_self.progress_slider.setEnabled(False)
			_self.device_list[i].playing = False
			_self.progress_slider.setValue(0)
			_self.stop_timer.emit(i)
			_self.device_list[i].time = QTime(0, 0, 0)
			_self.progress_label.setText(_self.device_list[i].time.toString("hh:mm:ss"))

	def split_seconds(self, s):
		hours = s // 3600
		minutes = (s - (hours * 3600)) // 60
		seconds = s - (minutes * 60)
		return hours, minutes, seconds

class StatusListener:
	def new_cast_status(self, status):
		_self = self._self
		i = _self.combo_box.currentIndex()
		index = self.index
		v = status.volume_level * 100
		if i != index:
			_self.device_list[index].volume = v
			_self.device_list[index].status_text = status.status_text
			return
		_self.device_list[i].volume = v
		_self.device_list[i].status_text = status.status_text
		_self.status_label.setText(status.status_text)
		if _self.dial_user_modified and _self.dial_value != v:
			return
		_self.dial_user_modified = False
		_self.dial.setValue(v)

if __name__ == '__main__':
	app = QApplication(sys.argv)
	ex = App()
	sys.exit(app.exec_())