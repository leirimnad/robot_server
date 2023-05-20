from abc import ABC, abstractmethod
from typing import Optional


class RobotThreadObserver(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def on_message_stack_update(self, message_stack: bytes):
        pass

    @abstractmethod
    def on_message_processed(self, message: Optional[bytes], response: bytes, new_message_stack: bytes):
        pass

    @abstractmethod
    def on_state_update(self, state_name):
        pass
