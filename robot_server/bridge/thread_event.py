from enum import Enum
from typing import Optional


class RobotThreadEvent:
    pass


class MessageStackUpdate(RobotThreadEvent):
    def __init__(self, message_stack: bytes):
        self.message_stack = message_stack


class MessageProcessed(RobotThreadEvent):
    def __init__(self, message: Optional[bytes], response: bytes, new_message_stack: bytes):
        self.message = message
        self.response = response
        self.new_message_stack = new_message_stack


class StateUpdate(RobotThreadEvent):
    def __init__(self, state_name: str):
        self.state_name = state_name


class MapState:
    class Rotation(Enum):
        UP = 0
        RIGHT = 1
        DOWN = 2
        LEFT = 3

    def __init__(self, position: tuple, rotation: Rotation, banned_positions: list[tuple[int, int]]):
        self.position = position
        self.rotation = rotation
        self.banned_positions = banned_positions


class MapUpdate(RobotThreadEvent):
    def __init__(self, map_state: MapState):
        self.map_state = map_state
