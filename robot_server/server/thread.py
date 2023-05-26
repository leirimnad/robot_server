import socket
import logging
from threading import Thread
from typing import Optional

from transitions import Machine, State
from .messages import ServerMessages, ClientMessage, ClientMessages
from .map import RobotMap
from .thread_observer import RobotThreadObserver
from robot_server.bridge.thread_event import StateUpdate, MessageProcessed, MessageStackUpdate, MapUpdate

logging.getLogger('transitions').setLevel(logging.WARNING)

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

arg_name = "message"


def get_message(**kwargs):
    global arg_name
    if arg_name not in kwargs.keys():
        raise NameError(f'"{arg_name}" not in kwargs')
    return kwargs.get(arg_name)


class MessageState(State):
    def __init__(self, supported_messages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        supported_messages = supported_messages if supported_messages is not None else []
        self.supported_messages: list[ClientMessage] = supported_messages if isinstance(supported_messages,
                                                                                        list) else [supported_messages]

    def exceeded_max_length(self, end_sequence, **kwargs):
        message: bytes = get_message(**kwargs)
        for i in reversed(range(len(end_sequence))):
            to_find = end_sequence[:i + 1]
            if message.endswith(to_find):
                message = message[:-len(to_find)]
                break
        kwargs.update({arg_name: message})
        return all(not m.length_check(**kwargs) for m in self.supported_messages)


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
        MessageState(name='error'),
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

        self.observers: list[RobotThreadObserver] = []
        self.message_in_process = None
        self.error: Optional[str] = None

        self.machine = Machine(model=self, states=RobotThread.states, initial='wait_username',
                               after_state_change=self.on_state_change)

        self.machine.add_transition('process_message', '*', 'recharging',
                                    conditions=ClientMessages.CLIENT_RECHARGING.syntax_check,
                                    before=self.save_before_charging_state)
        self.machine.add_transition('process_message', 'recharging', '=',
                                    conditions=ClientMessages.CLIENT_FULL_POWER.syntax_check,
                                    after=self.load_before_charging_state)
        self.machine.add_transition('process_message', 'recharging', 'error',
                                    before=lambda **kwargs: self.send_error(ServerMessages.SERVER_LOGIC_ERROR))

        self.machine.add_transition('process_message', 'wait_username', 'wait_key_id',
                                    conditions=ClientMessages.CLIENT_USERNAME.syntax_check,
                                    after=self.handle_correct_username)

        self.machine.add_transition('process_message', 'wait_key_id', 'wait_confirmation',
                                    conditions=ClientMessages.CLIENT_KEY_ID.logic_check,
                                    after=self.handle_correct_key_id)
        self.machine.add_transition('process_message', 'wait_key_id', 'error',
                                    conditions=ClientMessages.CLIENT_KEY_ID.syntax_check,
                                    before=lambda **kwargs: self.send_error(ServerMessages.SERVER_KEY_OUT_OF_RANGE_ERROR))

        self.machine.add_transition('process_message', 'wait_confirmation', 'wait_initial_client_ok',
                                    conditions=[ClientMessages.CLIENT_CONFIRMATION.syntax_check,
                                                self.check_client_hash],
                                    after=self.handle_correct_confirmation)
        self.machine.add_transition('process_message', 'wait_confirmation', 'error',
                                    conditions=ClientMessages.CLIENT_CONFIRMATION.syntax_check,
                                    before=lambda **kwargs: self.send_error(ServerMessages.SERVER_LOGIN_FAILED))

        self.machine.add_transition('process_message', ['wait_initial_client_ok', 'wait_client_ok'], 'wait_message',
                                    conditions=ClientMessages.CLIENT_OK.unique_check,
                                    after=self.handle_client_ok_center)
        self.machine.add_transition('process_message', ['wait_initial_client_ok', 'wait_client_ok'], 'wait_client_ok',
                                    conditions=ClientMessages.CLIENT_OK.syntax_check,
                                    after=self.handle_client_ok)

        self.machine.add_transition('process_message', 'wait_message', 'final',
                                    conditions=ClientMessages.CLIENT_MESSAGE.syntax_check,
                                    before=lambda **kwargs: self.send(ServerMessages.SERVER_LOGOUT))

        self.machine.add_transition('process_message',
                                    "*", 'error',
                                    before=lambda **kwargs: self.send_error(ServerMessages.SERVER_SYNTAX_ERROR))

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
        for observer in self.observers:
            observer.on_thread_event(MapUpdate(self.robot_map.get_map_state()))

    def handle_client_ok_center(self, **kwargs):
        new_position = ClientMessages.CLIENT_OK.parse(**kwargs)
        self.robot_map.update_position(new_position)
        for observer in self.observers:
            observer.on_thread_event(MapUpdate(self.robot_map.get_map_state()))
        self.send(ServerMessages.SERVER_PICK_UP)

    def on_enter_final(self, **kwargs):
        self.finish()

    def on_enter_error(self, **kwargs):
        self.finish()

    def finish(self):
        self.conn.close()
        self.stop_flag = True
        logging.info(f"{self.address} finished, stopping thread.")

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

    def add_observer(self, observer: RobotThreadObserver):
        self.observers.append(observer)
        observer.on_thread_event(StateUpdate(self.state, self.state in ["final", "error"], self.error))

    def on_state_change(self, **kwargs):
        for observer in self.observers:
            observer.on_thread_event(StateUpdate(self.state, self.state in ["final", "error"], self.error))

    def send(self, bytestring: bytes):
        to_send = bytestring + self.end_sequence
        logging.info(f"{self.address} <<< {to_send}")
        self.conn.sendall(to_send)
        for observer in self.observers:
            observer.on_thread_event(MessageProcessed(self.message_in_process, bytestring, self.message_stack))
        self.message_in_process = None

    def send_error(self, error: bytes):
        self.error = ServerMessages.get_error_message(error)
        self.send(error)

    def run(self):
        logging.info(f"(+) Thread working with address {self.address}")
        self.conn.settimeout(TIMEOUT)
        try:
            while True:
                if self.stop_flag:
                    return
                text = self.conn.recv(1024)
                logging.info(f"{self.address} >>> {text}")
                if text == b"":
                    self.error = "Closed by client"
                    self.to_error()
                    return

                self.message_stack += text

                for observer in self.observers:
                    observer.on_thread_event(MessageStackUpdate(self.message_stack))

                if not ClientMessages.matches_message(self.message_stack, self.end_sequence) \
                        and self.machine.get_state(self.state).exceeded_max_length(message=self.message_stack,
                                                                                   end_sequence=self.end_sequence):
                    logging.info(f"{self.address} used all length with message: {self.message_stack}")
                    self.send(ServerMessages.SERVER_SYNTAX_ERROR)
                    self.error = f"Exceeded length"
                    self.to_error()
                    self.conn.close()
                    return

                while ClientMessages.matches_message(self.message_stack, self.end_sequence):
                    message, rest = ClientMessages.parse_message(self.message_stack, self.end_sequence)
                    self.message_stack = rest
                    logging.info(f"{self.address} >=> {message}")
                    trimmed_message = message[:-len(self.end_sequence)]

                    self.message_in_process = trimmed_message
                    self.process_message(message=trimmed_message)
                    logging.info(f"{self.address} () State now: {self.state}")

        except socket.timeout:
            logging.info(f"{self.address} Timeout, disconnecting")
            self.error = f"Timeout"
            self.to_error()
            try:
                self.conn.close()
            except OSError:
                logging.warning(f"{self.address} Couldn't disconnect, possibly did already")
            return


