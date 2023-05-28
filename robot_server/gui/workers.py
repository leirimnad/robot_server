"""
This module contains the worker classes for the GUI.
"""

from PyQt5.QtCore import QObject, pyqtSignal, QThread

from robot_server.bridge.thread_event import RobotThreadEvent, MessageStackUpdate, \
    MessageProcessed, StateUpdate, MapUpdate
from robot_server.server import RobotServer, RobotServerObserver, RobotThread, RobotThreadObserver


class ServerWorkerMeta(type(RobotServerObserver), type(QObject)):
    """
    Metaclass for ServerWorker.
    Allows ServerWorker to inherit from QObject and RobotServerObserver at the
    same time.
    """


class ServerWorker(QObject, RobotServerObserver, metaclass=ServerWorkerMeta):
    """
    Class for the server worker.
    This class is responsible for starting the server and emitting signals
    when a new connection is made.
    """
    new_connection = pyqtSignal(object, name="newConnection")
    finished = pyqtSignal(name="finished")

    def __init__(self, server: RobotServer):
        """
        :param server: The RobotServer instance to use.
        """
        super().__init__()
        self._server = server
        self._server.add_observer(self)

    def on_new_connection(self, robot_thread: RobotThread):
        """
        Called by the RobotServer when a new connection is made.
        Creates a new RobotThreadWorker instance and emits the new_connection
        signal.
        :param robot_thread: The RobotThread instance that was created.
        """
        thread = QThread(None)
        thread_worker = ThreadWorker(robot_thread)
        thread_worker.moveToThread(thread)
        self.new_connection.emit(thread_worker)

    def start(self):
        """
        Starts the server.
        """
        self._server.start()

    def stop(self):
        """
        Calls the stop method of the server.
        """
        self._server.stop()


class ThreadWorkerMeta(type(RobotThreadObserver), type(QObject)):
    """
    Metaclass for ThreadWorker.
    Allows ThreadWorker to inherit from QObject and RobotThreadObserver at the
    same time.
    """


class ThreadWorker(QObject, RobotThreadObserver, metaclass=ThreadWorkerMeta):
    """
    Class for the thread worker.
    This class is responsible for emitting signals when a thread event occurs.
    This class stores events in a queue until the signals are connected.
    """
    message_stack_update = pyqtSignal(bytes, name="messageStackUpdate")
    message_processed = pyqtSignal(object, bytes, bytes, name="messageProcessed")
    state_update = pyqtSignal(str, bool, bool, str, name="stateUpdate")
    map_update = pyqtSignal(object, name="mapUpdate")
    disconnected = pyqtSignal(name="disconnected")

    def __init__(self, thread: RobotThread):
        """
        :param thread: The RobotThread instance to use.
        """
        super().__init__()
        self._thread = thread
        self._signals_connected = False
        self._events_queue = []
        self._thread.add_observer(self)
        self.connection_address = thread.address

    def _process_event(self, event: RobotThreadEvent):
        """
        Send the appropriate signal for the given event.
        :param event: The RobotThreadEvent to process.
        """
        if isinstance(event, MessageStackUpdate):
            self.message_stack_update.emit(event.message_stack)
        elif isinstance(event, MessageProcessed):
            self.message_processed.emit(event.message, event.response, event.new_message_stack)
        elif isinstance(event, StateUpdate):
            self.state_update.emit(
                event.state_name,
                event.final,
                event.error is not None, event.error
            )
            if event.final:
                self.disconnected.emit()
        elif isinstance(event, MapUpdate):
            self.map_update.emit(event.map_state)
        else:
            raise NotImplementedError

    def on_thread_event(self, event: RobotThreadEvent):
        """
        Called when a RobotThreadEvent occurs.
        Either processes the event or adds it to the queue.
        :param event: The RobotThreadEvent that occurred.
        """
        if not self._signals_connected:
            self._events_queue.append(event)
        else:
            self._process_event(event)

    def signals_connected(self):
        """
        Called when the signals are connected.
        Processes all events in the queue.
        """
        self._signals_connected = True
        for event in self._events_queue:
            self._process_event(event)
