"""
This module contains the RobotServerApplication class.
This class is the main class of the GUI. It is responsible for
starting the GUI and the server.
"""

import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread

from robot_server.server import RobotServer

from .main_window import MainWindow
from .workers import ServerWorker

# pylint: disable=too-few-public-methods


class RobotServerApplication:
    """
    Class for the application. This class is responsible for starting the GUI
    and the server.
    It starts the server by creating a ServerWorker instance and moving it to
    a QThread instance.
    """
    def __init__(self, robot_server: RobotServer):
        """
        :param robot_server: The RobotServer instance to use.
        """
        self._server_worker = None
        self._server_thread = None
        self._robot_server = robot_server
        self._app = QtWidgets.QApplication(sys.argv)
        self._main_window = MainWindow()

    def run(self):
        """
        Starts the GUI and the server.
        Connects the signals and slots of the GUI and the server workers.
        """
        self._main_window.show()
        self._server_worker = ServerWorker(self._robot_server)
        self._server_thread = QThread()
        self._server_worker.moveToThread(self._server_thread)
        self._server_thread.started.connect(self._server_worker.start)
        self._server_worker.new_connection.connect(self._main_window.on_new_connection)

        self._server_thread.start()
        self._app.exec()
