import socket
from threading import Thread
from transitions import Machine, State
from messages import ServerMessages, ClientMessage, ClientMessages
from robot_map import RobotMap

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

TIMEOUT = 1
TIMEOUT_RECHARGING = 5


class MessageState(State):
    def __init__(self, supported_messages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        supported_messages = supported_messages if supported_messages is not None else []
        self.supported_messages: list[ClientMessage] = supported_messages if isinstance(supported_messages,
                                                                                        list) else [supported_messages]

    def used_all_length(self, **kwargs):
        return all(m.used_length(**kwargs) for m in self.supported_messages)


class RobotThread(Thread):
    state_cls = MessageState
    end_sequence = b"\a\b"
    states = [
        MessageState(name='wait_username',
                     supported_messages=[ClientMessages.CLIENT_USERNAME, ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_key_id',
                     supported_messages=[ClientMessages.CLIENT_KEY_ID, ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_confirmation',
                     supported_messages=[ClientMessages.CLIENT_CONFIRMATION, ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_initial_client_ok',
                     supported_messages=[ClientMessages.CLIENT_OK, ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_client_ok',
                     supported_messages=[ClientMessages.CLIENT_OK, ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_message',
                     supported_messages=[ClientMessages.CLIENT_MESSAGE, ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='final'),
        MessageState(name='recharging', supported_messages=ClientMessages.CLIENT_FULL_POWER)
    ]

    def __init__(self, connection, address):
        Thread.__init__(self)
        self.conn = connection
        self.address = address
        self.message_stack = b""

        self.robot_username = None
        self.key_id = None
        self.username_hash = None
        self.stop_flag = False
        self.robot_map = RobotMap()
        self.before_charging_state = None

        self.machine = Machine(model=self, states=RobotThread.states, initial='wait_username')

        self.machine.add_transition('process_message', '*', 'recharging',
                                    conditions=ClientMessages.CLIENT_RECHARGING.syntax_check,
                                    before=self.save_before_charging_state)
        self.machine.add_transition('process_message', 'recharging', '=',
                                    conditions=ClientMessages.CLIENT_FULL_POWER.syntax_check,
                                    after=self.load_before_charging_state)
        self.machine.add_transition('process_message', 'recharging', 'final',
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_LOGIC_ERROR))

        self.machine.add_transition('process_message', 'wait_username', 'wait_key_id',
                                    conditions=ClientMessages.CLIENT_USERNAME.syntax_check,
                                    after=self.handle_correct_username)

        self.machine.add_transition('process_message', 'wait_key_id', 'wait_confirmation',
                                    conditions=ClientMessages.CLIENT_KEY_ID.logic_check,
                                    after=self.handle_correct_key_id)
        self.machine.add_transition('process_message', 'wait_key_id', 'final',
                                    conditions=ClientMessages.CLIENT_KEY_ID.syntax_check,
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_KEY_OUT_OF_RANGE_ERROR))

        self.machine.add_transition('process_message', 'wait_confirmation', 'wait_initial_client_ok',
                                    conditions=[ClientMessages.CLIENT_CONFIRMATION.syntax_check,
                                                self.check_client_hash],
                                    after=self.handle_correct_confirmation)
        self.machine.add_transition('process_message', 'wait_confirmation', 'final',
                                    conditions=ClientMessages.CLIENT_CONFIRMATION.syntax_check,
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_LOGIN_FAILED))

        self.machine.add_transition('process_message', ['wait_initial_client_ok', 'wait_client_ok'], 'wait_message',
                                    conditions=ClientMessages.CLIENT_OK.unique_check,
                                    after=lambda **kwargs: self.send(ServerMessages.SERVER_PICK_UP))
        self.machine.add_transition('process_message', ['wait_initial_client_ok', 'wait_client_ok'], 'wait_client_ok',
                                    conditions=ClientMessages.CLIENT_OK.syntax_check,
                                    after=self.handle_client_ok)

        self.machine.add_transition('process_message', 'wait_message', 'final',
                                    conditions=ClientMessages.CLIENT_MESSAGE.syntax_check,
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_LOGOUT))

        self.machine.add_transition('process_message',
                                    "*", 'final',
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_SYNTAX_ERROR))

    def handle_correct_username(self, **kwargs):
        self.robot_username = ClientMessages.CLIENT_USERNAME.parse(**kwargs)
        self.send(ServerMessages.SERVER_KEY_REQUEST)

    def handle_correct_key_id(self, **kwargs):
        self.key_id = ClientMessages.CLIENT_KEY_ID.parse(**kwargs)
        self.username_hash = self.compute_username_hash(self.robot_username)
        self.send(ServerMessages.server_confirmation(self.compute_server_hash()))

    def handle_correct_confirmation(self, **kwargs):
        self.send(ServerMessages.SERVER_OK)
        self.send(ServerMessages.SERVER_MOVE)

    def handle_client_ok(self, **kwargs):
        new_position = ClientMessages.CLIENT_OK.parse(**kwargs)
        self.send(ServerMessages.from_action(self.robot_map.update_position(new_position)))

    def on_enter_final(self, **kwargs):
        self.conn.close()
        self.stop_flag = True
        print(f"{self.address} Disconnected, stopping thread.")

    def check_client_hash(self, **kwargs) -> bool:
        client_hash = ClientMessages.CLIENT_CONFIRMATION.parse(**kwargs)
        right_hash = self.compute_client_hash()
        return client_hash == right_hash

    @staticmethod
    def compute_username_hash(username: str) -> int:
        return (sum(ord(c) for c in username) * 1000) % 65536

    def compute_server_hash(self) -> int:
        return (self.username_hash + server_keys.get(self.key_id)) % 65536

    def compute_client_hash(self) -> int:
        return (self.username_hash + client_keys.get(self.key_id)) % 65536

    def save_before_charging_state(self, **kwargs):
        self.before_charging_state = self.state

    def load_before_charging_state(self, **kwargs):
        getattr(self, f"to_{self.before_charging_state}")(**kwargs)

    def on_enter_recharging(self, **kwargs):
        self.conn.settimeout(TIMEOUT_RECHARGING)

    def on_exit_recharging(self, **kwargs):
        self.conn.settimeout(TIMEOUT)

    def send(self, bytestring: bytes):
        to_send = bytestring + self.end_sequence
        print(f"{self.address} <<< {to_send}")
        self.conn.sendall(to_send)

    def run(self):
        print(f"(+) Thread working with address {self.address}")
        self.conn.settimeout(TIMEOUT)
        try:
            while True:
                if self.stop_flag:
                    return
                text = self.conn.recv(1024)
                print(f"{self.address} >>> {text}")
                if text == b"":
                    self.conn.close()
                    return

                self.message_stack += text

                if not ClientMessages.matches_message(self.message_stack, self.end_sequence) \
                        and self.machine.get_state(self.state).used_all_length(message=self.message_stack):
                    print(f"{self.address} used all length with message: {self.message_stack}")
                    self.send(ServerMessages.SERVER_SYNTAX_ERROR)
                    self.conn.close()
                    return

                while ClientMessages.matches_message(self.message_stack, self.end_sequence):
                    message, rest = ClientMessages.parse_message(self.message_stack, self.end_sequence)
                    self.message_stack = rest
                    print(f"{self.address} >=> {message}")
                    trimmed_message = message[:-len(self.end_sequence)]

                    self.process_message(message=trimmed_message)
                    print(f"{self.address} () State now: {self.state}")

        except socket.timeout:
            print(f"{self.address} Timeout, disconnecting")
            try:
                self.conn.close()
            except OSError:
                print(f"{self.address} Couldn't disconnect, possibly did already")
            return


if __name__ == "__main__":

    HOST = "127.0.0.1"
    PORT = 61111
    threads = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        print(f"Started server on {HOST}, port {PORT}")
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
