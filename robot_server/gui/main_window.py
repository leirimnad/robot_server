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
        self.total_connections = 0
        self.totalConnectionsLabel.setText(str(self.total_connections))
        self.active_connections = 0
        self.activeConnectionsLabel.setText(str(self.active_connections))
        vbar = self.scrollArea.verticalScrollBar()
        vbar.rangeChanged.connect(lambda: vbar.setValue(vbar.maximum()))

    def on_new_connection(self, thread_worker: ThreadWorker):
        self.active_connections += 1
        self.total_connections += 1
        widget = ThreadWidget()

        thread_worker.message_stack_update.connect(widget.on_message_stack_update)
        thread_worker.message_processed.connect(widget.on_message_processed)
        thread_worker.state_update.connect(widget.on_state_update)
        thread_worker.map_update.connect(widget.on_map_update)
        thread_worker.disconnected.connect(self.on_disconnected)
        thread_worker.signals_connected()
        widget.set_connection_address(thread_worker.connection_address)

        self.threadWidgetsLayout.insertWidget(self.threadWidgetsLayout.count() - 1, widget)

        self.activeConnectionsLabel.setText(str(self.active_connections))
        self.totalConnectionsLabel.setText(str(self.total_connections))

    def on_disconnected(self):
        self.active_connections -= 1
        self.activeConnectionsLabel.setText(str(self.c))
