"""
Main window for the robot server GUI.
"""

from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5 import uic

from robot_server.gui.thread_widget import ThreadWidget
from robot_server.gui.workers import ThreadWorker


class MainWindow(QtWidgets.QMainWindow):
    """
    Class for creating and controlling the main window of the robot server GUI.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(Path(__file__).parent / "resources" / "main_window.ui", self)
        self.total_connections = 0
        self.totalConnectionsLabel.setText(str(self.total_connections))
        self.active_connections = 0
        self.activeConnectionsLabel.setText(str(self.active_connections))
        self.auto_scroll = True
        self._auto_scrolling__ = False
        self.vbar = self.scrollArea.verticalScrollBar()
        self.vbar.rangeChanged.connect(self.scroll_automatically)
        self.vbar.valueChanged.connect(self.on_scroll_value_changed)
        self.autoScrollCheckBox.stateChanged.connect(self.on_auto_scroll_checkbox_changed)
        self.setWindowTitle("Robot Server")
        icon_path = Path(__file__).parent / "resources" / "images" / "robot_icon.png"
        self.setWindowIcon(QIcon(str(icon_path)))

    def on_new_connection(self, thread_worker: ThreadWorker):
        """
        Should be called when a new connection is accepted by the server.
        :param thread_worker: The ThreadWorker instance for the new connection.
        """
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
        """
        Should be called when a connection is disconnected.
        """
        self.active_connections -= 1
        self.activeConnectionsLabel.setText(str(self.active_connections))

    def scroll_automatically(self):
        """
        Scrolls the scroll area to the bottom if auto scroll is enabled.
        Sets a temporary flag to prevent triggering the manual scroll event.
        """
        if self.auto_scroll:
            self._auto_scrolling__ = True
            self.vbar.setValue(self.vbar.maximum())

    def on_auto_scroll_checkbox_changed(self):
        """
        Called when the auto scroll checkbox is changed.
        Sets the auto scroll property to the value of the checkbox.
        If the checkbox is checked, the scroll area is scrolled to the bottom.
        Sets a temporary flag to prevent triggering the manual scroll event.
        """
        self._auto_scrolling__ = True
        self.vbar.setValue(self.vbar.maximum())
        self.auto_scroll = self.autoScrollCheckBox.isChecked()

    def on_scroll_value_changed(self):
        """
        Called when the scroll value is changed.
        If a temporary flag is set, the flag is unset and the function returns.
        Otherwise, turns off auto scroll and unchecks the auto scroll checkbox.
        """
        if self._auto_scrolling__:
            self._auto_scrolling__ = False
        else:
            self.auto_scroll = False
            self.autoScrollCheckBox.setChecked(False)
