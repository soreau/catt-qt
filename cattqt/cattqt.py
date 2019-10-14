# Copyright 2019 - Scott Moreau

import os
import sys
import math
import catt.api
import subprocess
from catt.api import CattDevice
import pychromecast
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QPoint, QTimer, QTime, QThread, pyqtSignal


def time_to_seconds(time):
    return time.hour() * 3600 + time.minute() * 60 + time.second()


class Device:
    def __init__(self, s, d, c, i):
        self.media_listener = MediaListener()
        self.media_listener._self = s
        self.media_listener.index = i
        self.status_listener = StatusListener()
        self.status_listener._self = s
        self.status_listener.index = i
        self.connection_listener = ConnectionListener()
        self.connection_listener._self = s
        self.cast = c
        self.index = i
        self._self = s
        self.device = d
        self.live = False
        self.muted = False
        self.unmute_volume = 0
        self.disconnect_volume = 0
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
        s = self._self
        self.time = self.time.addSecs(1)
        duration = self.device._cast.media_controller.status.duration
        if duration and duration != 0 and time_to_seconds(self.time) >= int(duration):
            # If progress is at the end, stop the device progress timer
            self.set_state_idle(self.index)
            if s.combo_box.currentIndex() == self.index:
                # If it is the currently selected device, update the ui
                self.update_ui_idle()
        if s.combo_box.currentIndex() == self.index:
            # Update the ui elements using current progress time
            s.progress_label.setText(self.time.toString("hh:mm:ss"))
            s.set_progress(time_to_seconds(self.time))

    def set_state_playing(self, i, time):
        s = self._self
        s.set_time(i, int(time))
        self.paused = False
        self.playing = True
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
        s.set_time(i, int(time))
        s.stop_timer.emit(i)
        self.paused = True
        self.playing = True

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
        v = self.device._cast.status.volume_level * 100
        s.dial.valueChanged.disconnect(s.on_dial_moved)
        if v != 0:
            self.unmute_volume = v
        s.dial.setValue(v)
        s.set_volume_label(v)
        s.dial.valueChanged.connect(s.on_dial_moved)

    def split_seconds(self, s):
        hours = s // 3600
        minutes = (s - (hours * 3600)) // 60
        seconds = s - ((hours * 3600) + (minutes * 60))
        return hours, minutes, seconds

    def update_text(self):
        s = self._self
        title = self.device._cast.media_controller.title
        status_text = self.device._cast.status.status_text
        prefix = ""
        if self.live:
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
        if prefix and (status_text or title):
            prefix = prefix + " - "
        if status_text and title:
            if status_text in title:
                s.status_label.setText(prefix + title)
            elif title in status_text:
                s.status_label.setText(prefix + status_text)
            else:
                s.status_label.setText(prefix + status_text + " - " + title)
        elif status_text:
            s.status_label.setText(prefix + status_text)
        elif title:
            s.status_label.setText(prefix + title)
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
        try:
            d.cast.reboot()
            print(d.device.name, "rebooting")
            self._self.play_button.setEnabled(False)
            self._self.stop_button.setEnabled(False)
            d.rebooting = True
        except:
            print(d.device.name, "reboot failed")
            pass


class Dial(QDial):
    def __init__(self, s):
        super(Dial, self).__init__()
        self._self = s

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._self.toggle_mute()


class SplashScreen(QSplashScreen):
    def __init__(self, pixmap, s):
        super(SplashScreen, self).__init__(pixmap)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setEnabled(False)
        self.painted = False
        self.version = s.version
        self.message = s.init_message
        self.showMessage(self.message)
        self.animation_radian = 0.0
        self.animation_radian = 0.0
        self.animation_frame_timer = QTimer()
        self.animation_trigger_timer = QTimer()
        self.animation_trigger_timer.setSingleShot(True)
        self.animation_frame_timer.timeout.connect(self.on_animation_frame)
        self.animation_trigger_timer.timeout.connect(self.on_animation_trigger)

    def on_animation_frame(self):
        self.animation_radian = (
            self.animation_radian
            + (3.0 - (math.cos(self.animation_radian) + 1.1)) * 0.05
        )
        if self.animation_radian >= math.radians(360):
            self.animation_frame_timer.stop()
            self.animation_trigger_timer.start(1000)
            self.animation_radian = 0.0
        self.update()

    def on_animation_trigger(self):
        self.animation_frame_timer.start(16)

    def drawContents(self, painter):
        w = painter.device().width()
        h = painter.device().height()
        painter.setRenderHint(QPainter.Antialiasing)
        roundRectPath = QPainterPath()
        roundRectPath.moveTo(0.0, 30.0)
        roundRectPath.arcTo(0.0, 0.0, 60.0, 60.0, 180.0, -90.0)
        roundRectPath.lineTo(290.0, 0.0)
        roundRectPath.arcTo(260.0, 0.0, 60.0, 60.0, 90.0, -90.0)
        roundRectPath.lineTo(320.0, 210.0)
        roundRectPath.arcTo(260.0, 180.0, 60.0, 60.0, 0.0, -90.0)
        roundRectPath.lineTo(30.0, 240.0)
        roundRectPath.arcTo(0.0, 180.0, 60.0, 60.0, 270.0, -90.0)
        roundRectPath.closeSubpath()
        painter.setPen(
            QPen(QColor(0, 0, 0, 0), 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        )
        brush = QLinearGradient(0, 0, 0, 100)
        brush.setColorAt(0.0, QColor(0, 0, 0, 127))
        painter.setBrush(brush)
        painter.drawPath(roundRectPath)
        qt_green = QColor(65, 205, 82)
        painter.setPen(QPen(qt_green, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        brush.setColorAt(0.0, qt_green)
        painter.setBrush(brush)
        hw = w / 2
        hh = h / 2
        head_width = 90
        head_height = 70
        animation_w = 10
        animation_h = 3
        angle = -self.animation_radian - math.radians(90)
        left_ear_tip_x = (math.cos(angle) * animation_w) + (
            (hw - head_width) + animation_w
        )
        left_ear_tip_y = (math.sin(angle) * animation_h) + (15 + animation_h)
        angle = self.animation_radian - math.radians(90)
        right_ear_tip_x = (math.cos(angle) * animation_w) + (
            (hw + head_width) - animation_w
        )
        right_ear_tip_y = (math.sin(angle) * animation_h) + (15 + animation_h)
        earsPath = QPainterPath()
        earsPath.moveTo((hw - head_width) + 5, hh)
        earsPath.lineTo(left_ear_tip_x, left_ear_tip_y)
        earsPath.lineTo(hw, hh - 50)
        earsPath.lineTo(right_ear_tip_x, right_ear_tip_y)
        earsPath.lineTo((hw + head_width) - 5, hh)
        earsPath.closeSubpath()
        painter.drawPath(earsPath)
        headPath = QPainterPath()
        headPath.moveTo(hw + head_width, hh)
        headPath.arcTo(
            hw - head_width,
            hh - head_height,
            head_width * 2,
            head_height * 2,
            0.0,
            360.0,
        )
        painter.drawPath(headPath)
        QSplashScreen.drawContents(self, painter)
        status_text_size = painter.fontMetrics().size(0, self.message)
        painter.setPen(QPen(Qt.white, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawStaticText(
            QPoint(
                hw - status_text_size.width() / 2, h - status_text_size.height() * 2
            ),
            QStaticText(self.message),
        )
        font = QFont()
        font.setPixelSize(75)
        font.setStyleStrategy(QFont.PreferAntialias)
        painter.setFont(font)
        qt_metrics = painter.fontMetrics()
        qt_text_size = qt_metrics.size(0, "Qt")
        painter.drawStaticText(
            QPoint(hw - qt_text_size.width() / 2, hh - qt_text_size.height() / 2),
            QStaticText("Qt"),
        )
        font.setPixelSize(25)
        painter.setFont(font)
        version_metrics = painter.fontMetrics()
        version_text_size = version_metrics.size(0, "v" + self.version)
        version_pos = QPoint(
            hw + qt_text_size.width() / 2 + version_text_size.width() / 2,
            ((hh - qt_text_size.width() / 2) + qt_metrics.ascent())
            - (version_metrics.ascent()),
        )
        painter.setPen(QPen(Qt.black, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawStaticText(
            QPoint(version_pos.x() + 1, version_pos.y() + 1),
            QStaticText("v" + self.version),
        )
        painter.setPen(QPen(Qt.white, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawStaticText(version_pos, QStaticText("v" + self.version))
        self.painted = True

    def showMessage(self, message, alignment=Qt.AlignLeft, color=Qt.black):
        pass

    def ensure_first_paint(self):
        while not self.painted:
            QThread.usleep(250)
            QApplication.processEvents()
        self.animation_trigger_timer.start(1000)

    def finish(self):
        self.animation_trigger_timer.stop()
        self.animation_frame_timer.stop()
        self.close()


class DiscoverThread(QThread):
    def __init__(self, s):
        super(DiscoverThread, self).__init__(s)
        self.s = s

    def run(self):
        self.s.devices = catt.api.discover()


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

    def resource_path(self, relative_path):
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            # Load from directory of script in case of pip
            base_path = os.path.dirname(os.path.realpath(__file__))

        return os.path.join(base_path, relative_path)

    def __init__(self, app, version):
        super().__init__()
        self.title = "Cast All The Things"
        self.init_message = "Scanning network for Chromecast devices.."
        self.app = app
        self.width = 640
        self.height = 1
        self.version = version
        self.reconnect_volume = -1
        if len(sys.argv) == 2 and sys.argv[1].startswith("--reconnect-volume="):
            try:
                arg = sys.argv[1]
                arg = arg[len("--reconnect-volume=") :]
                if int(arg) < 0 or int(arg) > 100:
                    raise Exception(
                        "Reconnect volume value out of range. Valid range is 0-100."
                    )
                else:
                    self.reconnect_volume = int(arg)
            except Exception as e:
                print(e)
        self.initUI()

    def discover_loop(self):
        self.splash.show()
        self.splash.ensure_first_paint()
        print(self.init_message)
        splash_thread = DiscoverThread(self)
        splash_thread.start()
        while splash_thread.isRunning():
            QThread.usleep(250)
            QApplication.processEvents()
        self.num_devices = len(self.devices)
        if self.num_devices == 0:
            self.splash.hide()
            print("No devices found")
            reply = QMessageBox.question(
                self,
                "catt-qt",
                "No devices found. Retry?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.discover_loop()
                return
            else:
                sys.exit(1)

    def initUI(self):
        self.splash = SplashScreen(QPixmap(320, 240), self)
        self.icon = QIcon(self.resource_path("chromecast.png"))
        self.splash.setWindowIcon(self.icon)
        self.discover_loop()
        self.setWindowTitle(self.title)
        self.setWindowIcon(self.icon)
        self.setGeometry(640, 480, self.width, self.height)
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
        if self.num_devices > 1:
            text = "devices found"
        else:
            text = "device found"
        print(self.num_devices, text)
        i = 0
        for d in self.devices:
            cast = pychromecast.Chromecast(d.ip_addr)
            cast.wait()
            device = Device(self, d, cast, i)
            cast.media_controller.register_status_listener(device.media_listener)
            cast.register_status_listener(device.status_listener)
            cast.register_connection_listener(device.connection_listener)
            device.disconnect_volume = round(cast.status.volume_level * 100)
            self.device_list.append(device)
            self.combo_box.addItem(d.name)
            if i == 0:
                device.set_dial_value()
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
        self.splash.finish()

    def play(self, d, text):
        if text == "" or (
            not "://" in text and not ":\\" in text and not text.startswith("/")
        ):
            self.status_label.setText("Failed to play, please use full path")
            print("Failed to play, please include full path")
            return
        self.status_label.setText("Playing..")
        subprocess.Popen(["catt", "-d", d.device.name, "cast", text])

    def on_play_click(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d == None:
            return
        if d.paused or d.live:
            if d.playing and not d.live:
                try:
                    d.device.play()
                except:
                    pass
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
            try:
                d.device.pause()
            except:
                pass
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
        duration = d.device._cast.media_controller.status.duration
        if duration != None:
            self.progress_slider.setMaximum(duration)
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
        duration = d.device._cast.media_controller.status.duration
        if duration:
            d.device.seek(duration - 3)

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
        else:
            d.unmute_volume = d.device._cast.status.volume_level * 100
            d.device.volume(0.0)

    def seek(self, d, value):
        self.status_label.setText("Seeking..")
        try:
            d.device.seek(value)
        except:
            pass

    def on_progress_value_changed(self):
        i = self.combo_box.currentIndex()
        d = self.get_device_from_index(i)
        if d.progress_clicked:
            return
        if d.device._cast.media_controller.status.supports_seek:
            v = self.progress_slider.value()
            self.stop_timer.emit(i)
            self.set_time(i, v)
            self.progress_label.setText(d.time.toString("hh:mm:ss"))
            duration = d.device._cast.media_controller.status.duration
            if duration and v != int(duration):
                self.seek(d, v)
        else:
            print("Stream does not support seeking")

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
        if d.device._cast.media_controller.status.supports_seek:
            if value > self.current_progress or value < self.current_progress:
                self.set_time(i, value)
                self.progress_label.setText(d.time.toString("hh:mm:ss"))
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

    def set_time(self, i, t):
        d = self.get_device_from_index(i)
        if d == None:
            return
        h, m, s = d.split_seconds(t)
        d.time.setHMS(h, m, s)

    def set_icon(self, button, icon):
        button.setIcon(self.app.style().standardIcon(getattr(QStyle, icon)))

    def event_pending_expired(self):
        self.volume_status_event_pending = False

    def on_add_device(self, ip):
        for d in self.device_list:
            if d.device.ip_addr == ip:
                last_volume = d.disconnect_volume
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
        self.volume_label.setEnabled(True)
        self.dial.setEnabled(True)
        device.disconnect_volume = last_volume
        if self.reconnect_volume == -1:
            if last_volume != round(device.cast.status.volume_level * 100):
                d.volume(last_volume / 100)
                if device.index == self.combo_box.currentIndex():
                    self.set_volume_label(last_volume)
        else:
            d.volume(self.reconnect_volume / 100)
            if device.index == self.combo_box.currentIndex():
                self.set_volume_label(self.reconnect_volume)

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
            self.skip_forward_button.setEnabled(False)
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.volume_label.setEnabled(False)
            self.dial.setEnabled(False)

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
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(v)
        self.progress_slider.blockSignals(False)

    def set_volume_label(self, v):
        self.volume_label.setText(self.volume_prefix + str(round(v)))


class MediaListener:
    def new_media_status(self, status):
        s = self._self
        i = s.combo_box.currentIndex()
        index = self.index
        if index == -1:
            return
        if i != index:
            d = s.get_device_from_index(index)
            if d == None:
                return
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
        d = s.get_device_from_index(i)
        if d == None:
            return
        v = round(status.volume_level * 100)
        d.disconnect_volume = v
        if i != index:
            return
        if d.muted and v != 0:
            d.muted = False
        elif not d.muted and v == 0:
            d.muted = True
        if not s.volume_status_event_pending:
            d.set_dial_value()
        else:
            s.set_volume_label(v)
            if v > 0:
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


def main(version) -> None:
    app = QApplication(sys.argv)
    ex = App(app, version)
    sys.exit(app.exec_())

author = "Scott Moreau"
email = "oreaus@gmail.com"
version = "2.5"

if __name__ == "__main__":
    main(version)
