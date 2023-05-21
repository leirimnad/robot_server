from abc import ABC, abstractmethod
from robot_server.bridge.thread_event import RobotThreadEvent


class RobotThreadObserver(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def on_thread_event(self, event: RobotThreadEvent):
        raise NotImplementedError
