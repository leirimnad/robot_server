from PyQt5 import QtWidgets
from PyQt5 import uic
from pathlib import Path

from robot_server.server import RobotServerObserver, RobotThread


class MainWindowMeta(type(QtWidgets.QWidget), type(RobotServerObserver)):
    pass


class MainWindow(QtWidgets.QMainWindow, RobotServerObserver, metaclass=MainWindowMeta):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(Path(__file__).parent / "resources" / "main_window.ui", self)

    def on_new_connection(self, robot_thread: RobotThread):
        self.label_2.setText(f"New connection at {robot_thread.address}")

