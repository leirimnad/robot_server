from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5 import uic

from robot_server.gui.thread_widget import ThreadWidget
from robot_server.server import RobotThread


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(Path(__file__).parent / "resources" / "main_window.ui", self)
        self.c = 0

    def on_new_connection(self, robot_thread: RobotThread):
        self.c += 1
        widget = ThreadWidget()
        robot_thread.add_observer(widget)
        self.label_2.setText(str(self.c))
        self.verticalLayout_3.addWidget(widget)
