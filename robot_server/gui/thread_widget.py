from pathlib import Path
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5 import uic

from ..server import RobotThreadObserver


class StateCategory:
    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def from_state_name(state_name: str):
        return {
            "wait_username": StateCategories.AUTHENTICATION,
            "wait_key_id": StateCategories.AUTHENTICATION,
            "wait_confirmation": StateCategories.AUTHENTICATION,
            "wait_initial_client_ok": StateCategories.NAVIGATION,
            "wait_client_ok": StateCategories.NAVIGATION,
            "wait_message": StateCategories.MESSAGE,
            "final": StateCategories.FINAL,
            "recharging": StateCategories.RECHARGING
        }.get(state_name)


class StateCategories:
    AUTHENTICATION = StateCategory("Authentication")
    NAVIGATION = StateCategory("Navigation")
    MESSAGE = StateCategory("Message")
    RECHARGING = StateCategory("Recharging")
    FINAL = StateCategory("Final")


class ThreadWidgetMeta(type(QtWidgets.QWidget), type(RobotThreadObserver)):
    pass


class ThreadWidget(QtWidgets.QWidget, metaclass=ThreadWidgetMeta):
    expected_categories = [StateCategories.AUTHENTICATION, StateCategories.NAVIGATION, StateCategories.MESSAGE]
    label_stylesheet = (Path(__file__).parent / "resources" / "stylesheets" / "categoryLabel.qss").read_text()
    label_selected_stylesheet = (
                Path(__file__).parent / "resources" / "stylesheets" / "categoryLabelSelected.qss").read_text()

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        uic.loadUi(Path(__file__).parent / "resources" / "thread_widget.ui", self)
        vbar = self.scrollArea.verticalScrollBar()
        vbar.rangeChanged.connect(lambda: vbar.setValue(vbar.maximum()))
        self._category: StateCategory = None
        self._selected_category = None
        self._categories_log: dict[StateCategory, list[tuple[Optional[bytes], bytes]]] = {}
        self._categories_labels: dict[StateCategory, QtWidgets.QLabel] = {}
        self.threadStateLabel.setText("Running")

    def on_message_stack_update(self, message_stack: bytes):
        self.incomingMessageLabel.setText(message_stack.decode())

    def on_message_processed(self, message: Optional[bytes], response: bytes, new_message_stack: bytes):

        self._categories_log[self._category].append((message, response))

        if self._category == self._selected_category:
            self._add_message(message, response)
            self.on_message_stack_update(new_message_stack)

    def on_state_update(self, state_name):
        new_category = StateCategory.from_state_name(state_name)
        self._category = new_category

        if new_category == StateCategories.FINAL:
            self.threadStateLabel.setText("Finished")
            return

        if new_category not in self._categories_log.keys():
            self._categories_log[new_category] = []
            label = QtWidgets.QLabel(new_category.name)
            label.setStyleSheet(self.label_stylesheet)
            label.mousePressEvent = lambda event: self.select_category(new_category)
            self._categories_labels[new_category] = label
            self.categoriesLayout.insertWidget(self.categoriesLayout.count() - 1, label)

        self.select_category(new_category)

    def select_category(self, category: StateCategory):
        if self._selected_category == category:
            return

        for label in self._categories_labels.values():
            label.setStyleSheet(self.label_stylesheet)

        self._categories_labels[category].setStyleSheet(self.label_selected_stylesheet)

        self._clear_message_layout()
        for i in self._categories_log[category]:
            self._add_message(*i)

        self._selected_category = category

    def _clear_message_layout(self):
        count = self.incomingMessagesLayout.count()
        for i in range(count - 2):
            incoming_message_item = self.incomingMessagesLayout.itemAt(0)
            incoming_message_widget = incoming_message_item.widget()
            self.incomingMessagesLayout.removeWidget(incoming_message_widget)
            incoming_message_widget.setParent(None)

            outgoing_message_item = self.outgoingMessagesLayout.itemAt(0)
            outgoing_message_widget = outgoing_message_item.widget()
            self.outgoingMessagesLayout.removeWidget(outgoing_message_widget)
            outgoing_message_widget.setParent(None)

    def _add_message(self, message: bytes, response: bytes):
        message_label = QtWidgets.QLabel(message.decode() if message else "")
        self.incomingMessagesLayout.insertWidget(self.incomingMessagesLayout.count() - 2, message_label)
        response_label = QtWidgets.QLabel(response.decode())
        self.outgoingMessagesLayout.insertWidget(self.outgoingMessagesLayout.count() - 2, response_label)