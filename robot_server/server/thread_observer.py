"""
This module defines the RobotThreadObserver class, which is an abstract class
for observers of the RobotThread class.
"""

from abc import ABC, abstractmethod
from robot_server.bridge.thread_event import RobotThreadEvent


class RobotThreadObserver(ABC):
    """
    Abstract class for observers of the RobotThread class.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self):
        pass

    @abstractmethod
    def on_thread_event(self, event: RobotThreadEvent):
        """
        Called when a RobotThreadEvent is emitted by the RobotThread.
        :param event: The RobotThreadEvent that was emitted.
        """
        raise NotImplementedError
