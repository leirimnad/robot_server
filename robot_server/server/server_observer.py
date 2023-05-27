"""
This file contains the RobotServerObserver class.
"""
from abc import ABC, abstractmethod

from .thread import RobotThread


class RobotServerObserver(ABC):
    """
    Abstract class for observers of the RobotServer class.
    """

    # pylint: disable=too-few-public-methods

    def __init__(self):
        pass

    @abstractmethod
    def on_new_connection(self, robot_thread: RobotThread):
        """
        Called when a new connection is accepted by the server.
        :param robot_thread: The RobotThread instance for the new connection.
        """
        raise NotImplementedError
