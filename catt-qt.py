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
		self.paused = True
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

	def create_devices_layout(self):
		self.devices_layout = QHBoxLayout()
		self.combo_box = QComboBox()
		self.devices_layout.addWidget(self.combo_box)

	def create_control_layout(self):
		self.control_layout = QHBoxLayout()
		self.dial = QDial()
		self.dial.setMinimum(0)
		self.dial.setMaximum(100)
		self.dial.setValue(0)
		self.dial_pressed = False
		self.dial_value = 0.0
		self.dial_user_modified = False
		self.dial.valueChanged.connect(self.on_dial_moved)
		self.dial.sliderPressed.connect(self.on_dial_pressed)
		self.dial.sliderReleased.connect(self.on_dial_released)
		self.textbox = QLineEdit()
		self.play_button = QPushButton()
		self.play_button.clicked.connect(self.on_play_click)
		self.set_icon(self.play_button, 'SP_MediaPlay')
		self.stop_button = QPushButton()
		self.stop_button.clicked.connect(self.on_stop_click)
		self.set_icon(self.stop_button, 'SP_MediaStop')
		self.control_layout.addWidget(self.play_button)
		self.control_layout.addWidget(self.stop_button)
		self.control_layout.addWidget(self.textbox)
		self.control_layout.addWidget(self.dial)

	def create_seek_layout(self):
		self.seek_layout = QHBoxLayout()
		self.progress_label = QLabel()
		self.progress_label.setText('00:00:00')
		self.progress_slider = QSlider(Qt.Horizontal)
		self.progress_slider.setValue(0)
		self.progress_slider.setEnabled(False)
		self.progress_slider.sliderPressed.connect(self.on_progress_pressed)
		self.progress_slider.sliderReleased.connect(self.on_progress_released)
		self.skip_forward_button = QPushButton()
		self.set_icon(self.skip_forward_button, 'SP_MediaSkipForward')
		self.seek_layout.addWidget(self.progress_label)
		self.seek_layout.addWidget(self.progress_slider)
		self.seek_layout.addWidget(self.skip_forward_button)

	def create_status_layout(self):
		self.status_layout = QHBoxLayout()
		self.status_label = QLabel()
		self.status_label.setText('Idle')
		self.status_label.setAlignment(Qt.AlignCenter)
		self.status_layout.addWidget(self.status_label)

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
		self.combo_box.currentIndexChanged.connect(self.on_index_changed)
		self.main_layout.addLayout(self.devices_layout)
		self.main_layout.addLayout(self.control_layout)
		self.main_layout.addLayout(self.seek_layout)
		self.main_layout.addLayout(self.status_layout)
		self.widget = QWidget()
		self.widget.setLayout(self.main_layout)
		self.setCentralWidget(self.widget)
		self.show()

	def on_play_click(self):
		d = self.device_list[self.combo_box.currentIndex()]
		if (self.play_button.icon().name() == 'media-playback-start'):
			if d.paused and d.playing:
				d.device.play()
				self.set_icon(self.play_button, 'SP_MediaPause')
				d.paused = False
				return
			text = self.textbox.text()
			if "://" in text:
				self.set_icon(self.play_button, 'SP_MediaPause')
				d.device.play_url(text, resolve=True, block=False)
		elif (self.play_button.icon().name() == 'media-playback-pause'):
			self.set_icon(self.play_button, 'SP_MediaPlay')
			d.device.pause()
			d.paused = True
			d.progress_timer.stop()

	def on_stop_click(self):
		i = self.combo_box.currentIndex()
		self.device_list[i].device.stop()
		self.stop_timer.emit(i)
		self.device_list[i].time = QTime(0, 0, 0)
		self.progress_slider.setValue(0)
		self.progress_label.setText(self.device_list[i].time.toString("hh:mm:ss"))
		self.set_icon(self.play_button, 'SP_MediaPlay')
		self.skip_forward_button.setEnabled(False)
		self.progress_slider.setEnabled(False)
		self.device_list[i].playing = False

	def on_index_changed(self):
		d = self.device_list[self.combo_box.currentIndex()]
		if d.playing and not d.paused:
			self.set_icon(self.play_button, 'SP_MediaPause')
		else:
			self.set_icon(self.play_button, 'SP_MediaPlay')
		self.skip_forward_button.setEnabled(d.playing)
		self.progress_slider.setEnabled(d.playing)
		self.progress_label.setText(d.time.toString("hh:mm:ss"))
		self.progress_slider.setMaximum(d.duration)
		self.progress_slider.setValue(time_to_seconds(d.time))
		self.dial.valueChanged.disconnect(self.on_dial_moved)
		self.dial.setValue(d.volume)
		self.dial.valueChanged.connect(self.on_dial_moved)
		self.status_label.setText(d.status_text)

	def on_skip_click(self):
		i = self.combo_box.currentIndex()
		self.device_list[i].device.seek(self.device_list[i].duration - 3)

	def on_dial_moved(self):
		self.device_list[self.combo_box.currentIndex()].device.volume(self.dial.value() / 100)

	def on_dial_pressed(self):
		self.dial_user_modified = True

	def on_dial_released(self):
		self.dial_value = self.dial.value()

	def on_progress_pressed(self):
		self.device_list[self.combo_box.currentIndex()].progress_timer.stop()
		self.current_progress = self.progress_slider.value()

	def on_progress_released(self):
		d = self.device_list[self.combo_box.currentIndex()]
		value = self.progress_slider.value()
		if d.media_listener.supports_seek:
			if value > self.current_progress:
				d.device.seek(value)
			elif value < self.current_progress:
				d.device.seek(value)
		else:
			print('Stream does not support seeking')

	def on_start_timer(self, i):
		self.device_list[i].progress_timer.start(1000)

	def on_stop_timer(self, i):
		self.device_list[i].progress_timer.stop()
		self.device_list[i].time.setHMS(0, 0, 0)

	def set_time(self, i, h, m, s):
		self.device_list[i].time.setHMS(h, m, s)

	def set_icon(self, button, icon):
		button.setIcon(app.style().standardIcon(getattr(QStyle, icon)))

class MediaListener:
	def new_media_status(self, status):
		_self = self._self
		i = _self.combo_box.currentIndex()
		index = self.index
		self.supports_seek = status.supports_seek
		if i != index:
			d = _self.device_list[index]
			if (status.player_state == 'PLAYING'):
				d.duration = status.duration
				hours, minutes, seconds = self.split_seconds(int(status.current_time))
				_self.set_time(index, hours, minutes, seconds)
				_self.start_timer.emit(index)
				d.paused = False
				d.playing = True
			elif (status.player_state == 'PAUSED'):
				d.duration = status.duration
				hours, minutes, seconds = self.split_seconds(int(status.current_time))
				_self.set_time(index, hours, minutes, seconds)
				d.paused = True
				d.playing = True
			elif ((status.player_state == 'IDLE' or status.player_state == 'UNKNOWN') and status.idle_reason == 'FINISHED'):
				_self.stop_timer.emit(index)
				d.time = QTime(0, 0, 0)
				d.playing = False
				d.paused = True
			return
		d = _self.device_list[i]
		if (status.player_state == 'PLAYING'):
			d.duration = status.duration
			_self.progress_slider.setMaximum(status.duration)
			_self.progress_slider.setValue(status.current_time)
			hours, minutes, seconds = self.split_seconds(int(status.current_time))
			_self.set_time(i, hours, minutes, seconds)
			_self.skip_forward_button.setEnabled(True)
			_self.progress_slider.setEnabled(True)
			d.paused = False
			d.playing = True
			_self.set_icon(_self.play_button, 'SP_MediaPause')
			_self.progress_label.setText(d.time.toString("hh:mm:ss"))
			_self.start_timer.emit(i)
		elif (status.player_state == 'PAUSED'):
			d.duration = status.duration
			_self.progress_slider.setMaximum(status.duration)
			_self.progress_slider.setValue(status.current_time)
			hours, minutes, seconds = self.split_seconds(int(status.current_time))
			_self.set_time(index, hours, minutes, seconds)
			_self.skip_forward_button.setEnabled(True)
			_self.progress_slider.setEnabled(True)
			d.paused = True
			d.playing = True
			_self.set_icon(_self.play_button, 'SP_MediaPlay')
			_self.progress_label.setText(d.time.toString("hh:mm:ss"))
		elif ((status.player_state == 'IDLE' or status.player_state == 'UNKNOWN') and status.idle_reason == 'FINISHED'):
			_self.set_icon(_self.play_button, 'SP_MediaPlay')
			_self.skip_forward_button.setEnabled(False)
			_self.progress_slider.setEnabled(False)
			d.playing = False
			d.paused = True
			_self.progress_slider.setValue(0)
			_self.stop_timer.emit(i)
			d.time = QTime(0, 0, 0)
			_self.progress_label.setText(d.time.toString("hh:mm:ss"))

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