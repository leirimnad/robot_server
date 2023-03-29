import socket
import re
from threading import Thread
from transitions import Machine


def re_check(re_str, arg_name="input"):
    def func(**kwargs):
        if arg_name not in kwargs.keys():
            raise NameError(f'"{arg_name}" not in kwargs')
        return re.match(re_str, kwargs.get(arg_name)) is not None

    return func


class RobotThread(Thread):
    end_sequence = b"\a\b"
    states = ['wait_username', 'wait_key_id', 'wait_confirmation', 'final']

    def __init__(self, connection, address):
        Thread.__init__(self)
        self.conn = connection
        self.address = address

        self.machine = Machine(model=self, states=RobotThread.states, initial='wait_username')
        self.machine.add_transition('username',
                                    'wait_username', 'wait_key_id',
                                    unless=[re_check(self.end_sequence + b".")],
                                    conditions=[re_check(b".{1,20}" + self.end_sequence)])
        self.machine.add_transition('username', 'wait_username', 'final')

    def run(self):
        print(f"Thread working with address {self.address}")
        while True:
            text = conn.recv(1024)
            print(f"{self.address}: {text}")
            self.username(input=text)
            print(f"{self.address} State now: {self.state}")


if __name__ == "__main__":

    HOST = "127.0.0.1"
    PORT = 61111

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print("Started")
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            RobotThread(conn, addr).start()
