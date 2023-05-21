from PyQt5.QtCore import QObject, pyqtSignal, QThread

from robot_server.bridge.thread_event import RobotThreadEvent, MessageStackUpdate, MessageProcessed, StateUpdate
from robot_server.server import RobotServer, RobotServerObserver, RobotThread, RobotThreadObserver


class ServerWorkerMeta(type(QObject), type(RobotServerObserver)):
    pass


class ServerWorker(QObject, RobotServerObserver, metaclass=ServerWorkerMeta):
    new_connection = pyqtSignal(object, name="newConnection")

    def __init__(self, server: RobotServer):
        super().__init__()
        self._server = server
        self._server.add_observer(self)

    def on_new_connection(self, robot_thread: RobotThread):
        print("UI: New connection signal emitted")
        thread = QThread(None)
        thread_worker = ThreadWorker(robot_thread)
        thread_worker.moveToThread(thread)
        print("UI: Thread worker up and running")
        self.new_connection.emit(thread_worker)

    def start(self):
        self._server.start()


class ThreadWorkerMeta(type(QObject), type(RobotThreadObserver)):
    pass


class ThreadWorker(QObject, RobotThreadObserver, metaclass=ThreadWorkerMeta):
    message_stack_update = pyqtSignal(bytes, name="messageStackUpdate")
    message_processed = pyqtSignal(object, bytes, bytes, name="messageProcessed")
    state_update = pyqtSignal(str, name="stateUpdate")

    def __init__(self, thread: RobotThread):
        super().__init__()
        self._thread = thread
        self._thread.add_observer(self)
        self._signals_connected = False
        self._events_queue = []

    def _process_event(self, event: RobotThreadEvent):
        if isinstance(event, MessageStackUpdate):
            self.message_stack_update.emit(event.message_stack)
        elif isinstance(event, MessageProcessed):
            self.message_processed.emit(event.message, event.response, event.new_message_stack)
        elif isinstance(event, StateUpdate):
            self.state_update.emit(event.state_name)
        else:
            raise NotImplementedError

    def on_thread_event(self, event: RobotThreadEvent):
        if not self._signals_connected:
            self._events_queue.append(event)
        else:
            self._process_event(event)

    def signals_connected(self):
        self._signals_connected = True
        for event in self._events_queue:
            self._process_event(event)
