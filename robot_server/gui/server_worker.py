from PyQt5.QtCore import QObject, pyqtSignal

from robot_server.server import RobotServer


class ServerWorker(QObject):

    def __init__(self, server: RobotServer):
        super().__init__()
        self._server = server

    def start(self):
        self._server.start()
