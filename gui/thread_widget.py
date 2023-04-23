import sys
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from robot_server.robot_thread_observer import RobotThreadObserver


class ThreadWidget(QtWidgets.QWidget, RobotThreadObserver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("resources/thread_widget.ui", self)

    def on_message_stack_update(self, message_stack: bytes):
        pass

    def on_message_processed(self, message: Optional[bytes], response: bytes, new_message_stack: bytes):
        pass

    def on_state_update(self, state_name):
        pass


app = QtWidgets.QApplication(sys.argv)
window = ThreadWidget()
window.show()
app.exec_()