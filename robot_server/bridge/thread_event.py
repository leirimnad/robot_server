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
