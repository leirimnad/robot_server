from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import QThread

from robot_server.gui.thread_widget import ThreadWidget
from robot_server.gui.workers import ThreadWorker
from robot_server.server import RobotThread


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(Path(__file__).parent / "resources" / "main_window.ui", self)
        self.c = 0
        vbar = self.scrollArea.verticalScrollBar()
        vbar.rangeChanged.connect(lambda: vbar.setValue(vbar.maximum()))

    def on_new_connection(self, thread_worker: ThreadWorker):
        self.c += 1
        widget = ThreadWidget()

        thread_worker.message_stack_update.connect(widget.on_message_stack_update)
        thread_worker.message_processed.connect(widget.on_message_processed)
        thread_worker.state_update.connect(widget.on_state_update)
        thread_worker.map_update.connect(widget.on_map_update)
        thread_worker.signals_connected()

        self.label_2.setText(str(self.c))
        self.verticalLayout_3.insertWidget(self.verticalLayout_3.count() - 1, widget)

