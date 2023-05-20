import sys

from PyQt5 import QtWidgets

from .main_window import MainWindow
from robot_server.server import RobotServer


class RobotServerApplication:
    def __init__(self, robot_server: RobotServer):
        self._robot_server = robot_server
        self._app = QtWidgets.QApplication(sys.argv)
        self._window = MainWindow()

    def run(self):
        self._window.show()
        self._app.exec()
