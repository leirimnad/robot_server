from PyQt5.QtCore import QObject, pyqtSignal

from robot_server.server import RobotServer, RobotServerObserver, RobotThread


class ServerWorkerMeta(type(QObject), type(RobotServerObserver)):
    pass


class ServerWorker(QObject, RobotServerObserver, metaclass=ServerWorkerMeta):
    new_connection = pyqtSignal(object, name="newConnection")

    def on_new_connection(self, robot_thread: RobotThread):
        self.new_connection.emit(robot_thread)

    def __init__(self, server: RobotServer):
        super().__init__()
        self._server = server
        self._server.add_observer(self)

    def start(self):
        self._server.start()
