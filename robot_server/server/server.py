import socket
import select

from .server_observer import RobotServerObserver
from .thread import RobotThread


class RobotServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.threads = []
        self.observers: list[RobotServerObserver] = []
        self._stopping = False

    def add_observer(self, observer: RobotServerObserver):
        self.observers.append(observer)

    def remove_observer(self, observer: RobotServerObserver):
        self.observers.remove(observer)

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print(f"Started server on {self.host}, port {self.port}")

        inputs = [server_socket]
        while not self._stopping:
            try:
                readable, _, _ = select.select(inputs, [], [], 1)
                for s in readable:
                    if self._stopping:
                        break
                    conn, addr = s.accept()
                    thread = RobotThread(conn, addr)
                    self.threads.append(thread)
                    for observer in self.observers:
                        observer.on_new_connection(thread)
                    thread.start()
            except OSError:
                if self._stopping:
                    break
                else:
                    raise
            except KeyboardInterrupt:
                self._stopping = True
                break

    def stop(self):
        for thread in self.threads:
            thread.to_final()
