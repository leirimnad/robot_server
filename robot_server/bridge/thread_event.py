"""
This module contains the events that are used to communicate between the
RobotThread and other applications.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


@dataclass
class RobotThreadEvent:
    """
    Abstract class for events that are used to communicate between the
    RobotThread and other applications.
    """


@dataclass
class MessageStackUpdate(RobotThreadEvent):
    """
    Event that is emitted when the message stack is updated.
    """
    def __init__(self, message_stack: bytes):
        """
        :param message_stack: The new message stack.
        """
        self.message_stack = message_stack


@dataclass
class MessageProcessed(RobotThreadEvent):
    """
    Event that is emitted when a message is processed.
    """
    def __init__(self,
                 message: Optional[bytes],
                 response: bytes,
                 new_message_stack: bytes):
        """
        :param message: The message that was processed.
        :param response: The response that was sent.
        :param new_message_stack: The new message stack.
        """
        self.message = message
        self.response = response
        self.new_message_stack = new_message_stack


@dataclass
class StateUpdate(RobotThreadEvent):
    """
    Event that is emitted when the state of the RobotThread is updated.
    """
    def __init__(self,
                 state_name: str,
                 final: bool = False,
                 error: Optional[Exception] = None):
        """
        :param state_name: The name of the new state.
        :param final: Whether the new state is final.
        :param error: The error that occurred, if any.
        """
        self.state_name = state_name
        self.final = final
        self.error = error


@dataclass
class MapState:
    """
    Class that represents the state of the map.
    """

    # pylint: disable=duplicate-code
    # disable duplicate-code because the Rotation class is a bridge between the
    # server and the gui

    class Rotation(Enum):
        """
        Enum that represents the rotation of the robot.
        """
        UP = 0
        RIGHT = 1
        DOWN = 2
        LEFT = 3

    def __init__(self,
                 position: tuple,
                 rotation: Rotation,
                 obstacles: list[tuple[int, int]]):
        """
        :param position: The position of the robot.
        :param rotation: The rotation of the robot.
        :param obstacles: The obstacles on the map.
        """
        self.position = position
        self.rotation = rotation
        self.obstacles = obstacles


@dataclass
class MapUpdate(RobotThreadEvent):
    """
    Event that is emitted when the map is updated.
    """
    def __init__(self, map_state: MapState):
        """
        :param map_state: The new state of the map.
        """
        self.map_state = map_state
