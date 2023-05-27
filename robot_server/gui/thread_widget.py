"""
This module contains the ThreadWidget class, which is a widget that displays the state of a thread.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5 import uic

from .map_drawer import MapDrawer
from ..bridge.thread_event import MapState
from ..server import RobotThreadObserver


@dataclass(eq=False)
class StateCategory:
    """
    Class for representing a category of states.
    Should be used to split the states of robot's state machine into human-readable categories.
    """

    def __init__(self, name: str):
        """
        :param name: The name of the category.
        """
        self.name = name

    @staticmethod
    def from_state_name(state_name: str):
        """
        Returns the category for the given state name.
        :param state_name: The name of the state of robot's state machine.
        """
        return {
            "wait_username": StateCategories.AUTHENTICATION,
            "wait_key_id": StateCategories.AUTHENTICATION,
            "wait_confirmation": StateCategories.AUTHENTICATION,
            "wait_initial_client_ok": StateCategories.NAVIGATION,
            "wait_client_ok": StateCategories.NAVIGATION,
            "wait_message": StateCategories.MESSAGE,
            "final": StateCategories.FINAL,
            "error": StateCategories.ERROR,
            "recharging": StateCategories.RECHARGING
        }.get(state_name)


@dataclass
class StateCategories:
    """
    Class containing all the state categories.
    """
    NONE = StateCategory("None")
    AUTHENTICATION = StateCategory("Authentication")
    NAVIGATION = StateCategory("Navigation")
    MESSAGE = StateCategory("Message")
    RECHARGING = StateCategory("Recharging")
    FINAL = StateCategory("Final")
    ERROR = StateCategory("Error")


class ThreadWidgetMeta(type(RobotThreadObserver), type(QtWidgets.QWidget)):
    """
    Metaclass for the ThreadWidget class.
    Allows the ThreadWidget class to inherit from both QtWidgets.QWidget and RobotThreadObserver.
    """


# pylint: disable=too-many-instance-attributes

class ThreadWidget(QtWidgets.QWidget, metaclass=ThreadWidgetMeta):
    """
    Widget that displays the state of a thread.
    The widget is divided into categories, each category contains the states
    of the thread that belong to that category.
    For each category it can display the messages that the server has received and sent.
    The widget contains a map that displays the robot's position.
    """
    label_stylesheet = (Path(__file__).parent / "resources" / "stylesheets" / "categoryLabel.qss") \
        .read_text()
    label_selected_stylesheet = (
            Path(__file__).parent / "resources" / "stylesheets" / "categoryLabelSelected.qss") \
        .read_text()
    label_expected_stylesheet = (
            Path(__file__).parent / "resources" / "stylesheets" / "categoryLabelExpected.qss") \
        .read_text()
    label_skipped_stylesheet = (
            Path(__file__).parent / "resources" / "stylesheets" / "categoryLabelSkipped.qss"). \
        read_text()

    def __init__(self, *args, parent=None, **kwargs):
        """
        :param parent: The parent widget.
        """
        super().__init__(parent=parent, *args, **kwargs)
        uic.loadUi(Path(__file__).parent / "resources" / "thread_widget.ui", self)
        vbar = self.scrollArea.verticalScrollBar()
        vbar.rangeChanged.connect(lambda: vbar.setValue(vbar.maximum()))
        self._category: StateCategory = StateCategories.NONE
        self._selected_category = None
        self._categories_log: dict[StateCategory, list[tuple[Optional[bytes], bytes]]] = {}
        self._categories_labels: dict[StateCategory, QtWidgets.QLabel] = {}
        self._expected_categories = [
            StateCategories.AUTHENTICATION,
            StateCategories.NAVIGATION,
            StateCategories.MESSAGE
        ]
        self._expected_categories_labels: dict[StateCategory, QtWidgets.QLabel] = {}
        self._message_stack = ""
        self._category_manually_selected = False
        self._map_drawer = MapDrawer(self.mapGraphicsView)

        self.threadStateLabel.setText("Running")

        for category in self._expected_categories:
            label = QtWidgets.QLabel(category.name)
            label.setStyleSheet(self.label_expected_stylesheet)
            self._expected_categories_labels[category] = label
            self.categoriesLayout.insertWidget(self.categoriesLayout.count() - 1, label)

    def on_message_stack_update(self, message_stack: bytes):
        """
        Updates graphical representation of the message stack.
        :param message_stack: The message stack.
        """
        self._message_stack = repr(message_stack.decode())[1:-1]

        if self._category == self._selected_category:
            self.incomingMessageLabel.setText(self._message_stack)

    def on_message_processed(self,
                             message: Optional[bytes],
                             response: bytes,
                             new_message_stack: bytes):
        """
        Updates the representation of the messages that the server has received and sent.
        Updates the representation of the message stack.
        :param message: The message that the server is responding to or None if the server
        is sending a message.
        :param response: The response of the server or the message that the server is sending.
        :param new_message_stack: The new message stack.
        """

        self._categories_log[self._category].append((message, response))

        if self._category == self._selected_category:
            self._add_message(message, response)
            self.on_message_stack_update(new_message_stack)

    def on_state_update(self, state_name: str, final: bool, error_bool: bool, error: Optional[str]):
        """
        Updates the state of the thread.
        Creates the graphical representation of the category if the state belongs
        to a new category.
        If the category is not among the expected categories, the category is skipped.
        If the state is final displays the final label.
        If the state is an error displays the error label with the error message.

        :param state_name: The name of the state of robot's state machine.
        :param final: True if the state is final or error occurred.
        :param error_bool: True if the state is an error.
        :param error: The error message.
        """
        new_category = StateCategory.from_state_name(state_name)
        self._category = new_category

        if final:
            if error_bool:
                # error bool is crazy, but signals return empty strings even when they are None
                self._finish_with_error(error)
                return
            self._finish()
            return

        if new_category not in self._categories_log:
            self._categories_log[new_category] = []

            if len(self._expected_categories) > 0 and new_category == self._expected_categories[0]:
                self._expected_categories.pop(0)
                self.categoriesLayout.removeWidget(self._expected_categories_labels[new_category])
                self._expected_categories_labels[new_category].setParent(None)
                del self._expected_categories_labels[new_category]

                label = QtWidgets.QLabel(new_category.name)
                label.setStyleSheet(self.label_stylesheet)
                label.mousePressEvent = lambda event: self.select_category(new_category, True)
                self._categories_labels[new_category] = label
                self.categoriesLayout.insertWidget(
                    self.categoriesLayout.count() - len(self._expected_categories) - 1, label)

                if not self._category_manually_selected:
                    self.select_category(new_category)

    def select_category(self, category: StateCategory, manually_selected=False):
        """
        Selects the category and displays the messages of the category.
        If the category is already selected, does nothing.
        If manually_selected is True, won't change the category when the state changes.
        :param category: The category to select.
        :param manually_selected: True if the category was selected manually.
        """
        if self._selected_category == category:
            return

        if manually_selected:
            self._category_manually_selected = True

        for label in self._categories_labels.values():
            label.setStyleSheet(self.label_stylesheet)

        self._categories_labels[category].setStyleSheet(self.label_selected_stylesheet)

        self._clear_message_layout()
        for i in self._categories_log[category]:
            self._add_message(*i)

        if self._category == category:
            self.incomingMessageLabel.setText(self._message_stack)
        else:
            self.incomingMessageLabel.setText("")

        self._selected_category = category

    def on_map_update(self, map_state: MapState):
        """
        Updates the map representation.
        :param map_state: The map state.
        """
        self._map_drawer.update_map(map_state)

    def set_connection_address(self, address: tuple[str, int]):
        """
        Sets the address of the connection.
        :param address: The address of the connection as a tuple of ip address and port.
        """
        self.addressLabel.setText(f"{address[0]}:{address[1]}")

    def _finish(self):
        """
        Displays the final label.
        For expected categories that haven't been reached, updates
        their style sheet to label_skipped_stylesheet.
        """
        self.threadStateLabel.setText("Finished")
        self.threadStateLabel.setStyleSheet("color: green;")
        for label in self._expected_categories_labels.values():
            label.setStyleSheet(self.label_skipped_stylesheet)

    def _finish_with_error(self, error: str):
        """
        Displays the error label with the error message.
        For expected categories that haven't been reached, updates
        their style sheet to label_skipped_stylesheet.
        """
        self.threadStateLabel.setText(error)
        self.threadStateLabel.setStyleSheet("color: red;")
        self.incomingMessageLabel.setStyleSheet("color: #b35b5b;")
        for label in self._expected_categories_labels.values():
            label.setStyleSheet(self.label_skipped_stylesheet)

    def _clear_message_layout(self):
        """
        Clears the message layout.
        """
        count = self.incomingMessagesLayout.count()
        for _ in range(count - 2):
            incoming_message_item = self.incomingMessagesLayout.itemAt(0)
            incoming_message_widget = incoming_message_item.widget()
            self.incomingMessagesLayout.removeWidget(incoming_message_widget)
            incoming_message_widget.setParent(None)

            outgoing_message_item = self.outgoingMessagesLayout.itemAt(0)
            outgoing_message_widget = outgoing_message_item.widget()
            self.outgoingMessagesLayout.removeWidget(outgoing_message_widget)
            outgoing_message_widget.setParent(None)

    def _add_message(self, message: bytes, response: bytes):
        """
        Adds a message to the message layout.
        :param message: The message that the server has received.
        :param response: The response that the server is sending.
        """
        message_label = QtWidgets.QLabel(message.decode() if message else "")
        self.incomingMessagesLayout.insertWidget(
            self.incomingMessagesLayout.count() - 2,
            message_label
        )
        response_label = QtWidgets.QLabel(response.decode())
        self.outgoingMessagesLayout.insertWidget(
            self.outgoingMessagesLayout.count() - 2,
            response_label
        )
