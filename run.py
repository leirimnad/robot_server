import socket
import re
from threading import Thread
from transitions import Machine
from messages import ServerMessages, ClientMessages

server_keys = {
    0: 23019,
    1: 32037,
    2: 18789,
    3: 16443,
    4: 18189
}

client_keys = {
    0: 32037,
    1: 29295,
    2: 13603,
    3: 29533,
    4: 21952
}


class RobotThread(Thread):
    end_sequence = b"\a\b"
    states = ['wait_username', 'wait_key_id', 'wait_confirmation', 'wait_initial_client_ok', 'wait_client_ok', 'final']
    client_checks = ClientMessages(end_sequence=end_sequence, arg_name="message")

    def __init__(self, connection, address):
        Thread.__init__(self)
        self.conn = connection
        self.address = address

        self.robot_username = None
        self.key_id = None
        self.server_hash = None
        self.stop_flag = False
        self.position = None
        self.rotation = None

        self.machine = Machine(model=self, states=RobotThread.states, initial='wait_username')
        self.machine.add_transition('process_message', 'wait_username', 'wait_key_id',
                                    conditions=self.client_checks.username)

        self.machine.add_transition('process_message', 'wait_key_id', 'wait_confirmation',
                                    conditions=self.client_checks.key_id)
        self.machine.add_transition('process_message', 'wait_key_id', 'final',
                                    conditions=self.client_checks.key_id_syntax,
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_KEY_OUT_OF_RANGE_ERROR)
                                    )

        self.machine.add_transition('process_message', 'wait_confirmation', 'wait_initial_client_ok',
                                    conditions=self.check_client_hash)
        self.machine.add_transition('process_message', 'wait_confirmation', 'final',
                                    conditions=self.client_checks.confirmation_syntax,
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_LOGIN_FAILED))

        self.machine.add_transition('process_message', 'wait_initial_client_ok', 'wait_client_ok',
                                    conditions=self.client_checks.ok)

        self.machine.add_transition('process_message',
                                    "*", 'final',
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_SYNTAX_ERROR))

    def on_enter_wait_key_id(self, **kwargs):
        self.robot_username = (re.match(b"(.{1,20})" + self.end_sequence, kwargs.get("message")).group(1)).decode()
        self.send(ServerMessages.SERVER_KEY_REQUEST)

    def on_enter_wait_confirmation(self, **kwargs):
        self.key_id = int(re.match(b"([01234])" + self.end_sequence, kwargs.get("message")).group(1))
        self.server_hash = self.compute_server_hash(self.robot_username, server_keys.get(self.key_id))
        self.send(ServerMessages.server_confirmation(self.server_hash))

    def on_enter_wait_initial_client_ok(self, **kwargs):
        self.send(ServerMessages.SERVER_OK)
        self.send(ServerMessages.SERVER_MOVE)

    def on_enter_wait_client_ok(self, **kwargs):
        new_position = self.client_checks.parse_position(**kwargs)
        if new_position == self.position:  # obstacle
            pass
        

    def on_enter_final(self, **kwargs):
        self.conn.close()
        self.stop_flag = True
        print(f"{self.address} Disconnected, stopping thread.")

    def check_client_hash(self, **kwargs) -> bool:
        return kwargs.get("message") == str(self.compute_client_hash(
            self.server_hash,
            client_keys.get(self.key_id)
        )).encode() + self.end_sequence

    @staticmethod
    def compute_server_hash(username: str, server_key: int) -> int:
        return (((sum(ord(c) for c in username) * 1000) % 65536) + server_key) % 65536

    @staticmethod
    def compute_client_hash(server_hash: int, client_key: int) -> int:
        return (server_hash + client_key) % 65536

    def send(self, bytestring: bytes):
        print(f"{self.address} <<< {bytestring}")
        self.conn.sendall(bytestring + self.end_sequence)

    def run(self):
        print(f"Thread working with address {self.address}")
        while True:
            if self.stop_flag:
                return
            text = conn.recv(1024)
            print(f"{self.address} >>> {text}")
            if text == b"":
                self.conn.close()
                return
            self.process_message(message=text)
            print(f"{self.address} () State now: {self.state}")


if __name__ == "__main__":

    HOST = "127.0.0.1"
    PORT = 61111
    threads = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print("Started")
        s.bind((HOST, PORT))
        s.listen()
        while True:
            try:
                conn, addr = s.accept()
                thread = RobotThread(conn, addr)
                threads.append(thread)
                thread.start()
            except KeyboardInterrupt:
                break
        for thread in threads:
            thread.to_final()
