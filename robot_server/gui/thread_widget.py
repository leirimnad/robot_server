from pathlib import Path
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5 import uic

from ..server import RobotThreadObserver


class ThreadWidgetMeta(type(QtWidgets.QWidget), type(RobotThreadObserver)):
    pass


class ThreadWidget(QtWidgets.QWidget, metaclass=ThreadWidgetMeta):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        uic.loadUi(Path(__file__).parent / "resources" / "thread_widget.ui", self)
        vbar = self.scrollArea.verticalScrollBar()
        vbar.rangeChanged.connect(lambda: vbar.setValue(vbar.maximum()))

    def on_message_stack_update(self, message_stack: bytes):
        self.incomingMessageLabel.setText(message_stack.decode())

    def on_message_processed(self, message: Optional[bytes], response: bytes, new_message_stack: bytes):
        message_label = QtWidgets.QLabel(message.decode() if message else "")
        self.incomingMessagesLayout.insertWidget(self.incomingMessagesLayout.count() - 2, message_label)
        response_label = QtWidgets.QLabel(response.decode())
        self.outgoingMessagesLayout.insertWidget(self.outgoingMessagesLayout.count() - 2, response_label)
        self.on_message_stack_update(new_message_stack)

    def on_state_update(self, state_name):
        self.threadStateLabel.setText(state_name)
