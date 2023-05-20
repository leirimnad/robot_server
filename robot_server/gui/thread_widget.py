import sys
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5 import uic

from ..server.thread_observer import RobotThreadObserver


class ThreadWidgetMeta(type(QtWidgets.QWidget), type(RobotThreadObserver)):
    pass


class ThreadWidget(QtWidgets.QWidget, RobotThreadObserver, metaclass=ThreadWidgetMeta):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("resources/thread_widget.ui", self)

    def on_message_stack_update(self, message_stack: bytes):
        self.label_6.setText(message_stack.decode())

    def on_message_processed(self, message: Optional[bytes], response: bytes, new_message_stack: bytes):
        self.label_7.setText(response.decode())
        self.label_8.setText(message.decode())
        self.label_6.setText(new_message_stack.decode())

    def on_state_update(self, state_name):
        self.label.setText(state_name)


app = QtWidgets.QApplication(sys.argv)
window = ThreadWidget()
window.show()
app.exec_()
