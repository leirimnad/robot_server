from abc import ABC, abstractmethod

from robot_server.server import RobotThread


class RobotServerObserver(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def on_new_connection(self, robot_thread: RobotThread):
        raise NotImplementedError
