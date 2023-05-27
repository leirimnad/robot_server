"""
This module contains the RobotServer class, which is responsible for
accepting new connections and creating RobotThread instances for them.
"""

import socket
import select

from .server_observer import RobotServerObserver
from .thread import RobotThread


class RobotServer:
    """
    Class for the server, which is responsible for accepting new connections
    and creating RobotThread instances for them.
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.threads = []
        self.observers: list[RobotServerObserver] = []
        self._stopping = False

    def add_observer(self, observer: RobotServerObserver):
        """
        Add an observer to the server.
        :param observer: The observer to add.
        """
        self.observers.append(observer)

    def remove_observer(self, observer: RobotServerObserver):
        """
        Remove an observer from the server.
        :param observer: The observer to remove.
        """
        self.observers.remove(observer)

    def start(self):
        """
        Starts the server.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print(f"Started server on {self.host}, port {self.port}")

        inputs = [server_socket]
        while not self._stopping:
            try:
                readable, _, _ = select.select(inputs, [], [], 1)
                for readable_socket in readable:
                    if self._stopping:
                        break
                    conn, addr = readable_socket.accept()
                    thread = RobotThread(conn, addr)
                    self.threads.append(thread)
                    for observer in self.observers:
                        observer.on_new_connection(thread)
                    thread.start()
            except OSError:
                if self._stopping:
                    break
                raise
            except KeyboardInterrupt:
                self._stopping = True
                break

    def stop(self):
        """
        Stops the server.
        Sets the state of all threads to final.
        """
        for thread in self.threads:
            thread.to_final()
