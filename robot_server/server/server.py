import socket
from .thread import RobotThread


class RobotServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.threads = []
        self.observers = []

    def add_observer(self, observer):
        self.observers.append(observer)

    def remove_observer(self, observer):
        self.observers.remove(observer)

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            print(f"Started server on {self.host}, port {self.port}")
            s.listen()
            while True:
                try:
                    conn, addr = s.accept()
                    thread = RobotThread(conn, addr)
                    self.threads.append(thread)
                    for observer in self.observers:
                        observer.on_new_connection(thread)
                    thread.start()
                except KeyboardInterrupt:
                    break
            for thread in self.threads:
                thread.to_final()
