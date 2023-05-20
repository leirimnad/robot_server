import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread

from .main_window import MainWindow
from robot_server.server import RobotServer
from .server_worker import ServerWorker


class RobotServerApplication:
    def __init__(self, robot_server: RobotServer):
        self._server_worker = None
        self._server_thread = None
        self._robot_server = robot_server
        self._app = QtWidgets.QApplication(sys.argv)
        self._main_window = MainWindow()

        robot_server.add_observer(self._main_window)

    def run(self):
        self._main_window.show()
        self._server_worker = ServerWorker(self._robot_server)
        self._server_thread = QThread()
        self._server_worker.moveToThread(self._server_thread)
        self._server_thread.started.connect(self._server_worker.start)

        self._server_thread.start()
        self._app.exec()
