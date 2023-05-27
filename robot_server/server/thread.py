"""
Thread that handles the communication with the client.
It is in charge of the authentication and the message processing.
The message processing is done by using a state machine.
"""

# pylint: disable=too-many-instance-attributes,unused-argument,no-member
# unused-argument is disabled because the transitions library passes \
# the arguments as mandatory keyword arguments
# no-member is disabled because the transitions library creates the \
# attributes dynamically

import socket
import logging
from threading import Thread
from typing import Optional

from transitions import Machine, State

from robot_server.bridge.thread_event import StateUpdate, MessageProcessed, \
    MessageStackUpdate, MapUpdate

from .messages import ServerMessages, ClientMessage, ClientMessages
from .map import RobotMap
from .thread_observer import RobotThreadObserver


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

ARG_NAME = "message"


def get_message(**kwargs):
    """
    The get_message function takes a keyword argument and returns the value of that argument.
    The reason for this function is that the transitions library passes only keyword
    arguments to the state functions.

    :return: The value of the argument that is passed in
    """
    if ARG_NAME not in kwargs:
        raise NameError(f'"{ARG_NAME}" not in kwargs')
    return kwargs.get(ARG_NAME)


class MessageState(State):
    """
    The MessageState class is a subclass of the transitions library's State class.
    It is used to check if a message could be of a type that is supported by the state.
    """
    def __init__(self, *args, supported_messages=None, **kwargs):
        super().__init__(*args, **kwargs)
        supported_messages = supported_messages \
            if supported_messages is not None else []
        self.supported_messages: list[ClientMessage] = supported_messages \
            if isinstance(supported_messages, list) else [supported_messages]

    def exceeded_max_length(self, end_sequence, **kwargs):
        """
        The exceeded_max_length function is used to determine if the message has exceeded
        the maximum possible length for all the supported message types.
        If the suffix of the message is a prefix of the end_sequence, then the message is
        truncated by the length of the suffix.

        :param end_sequence: End sequence of the message
        :return: True if the message is longer than the maximum length
        """
        message: bytes = get_message(**kwargs)
        for i in reversed(range(len(end_sequence))):
            to_find = end_sequence[:i + 1]
            if message.endswith(to_find):
                message = message[:-len(to_find)]
                break
        kwargs.update({ARG_NAME: message})
        return all(not m.length_check(**kwargs) for m in self.supported_messages)


class RobotThread(Thread):
    """
    The RobotThread class represents a thread that handles the communication with the client.
    It is in charge of the authentication and the message processing.
    The message processing is done by using a state machine.
    """
    state_cls = MessageState
    end_sequence = b"\a\b"
    states = [
        MessageState(name='wait_username',
                     supported_messages=[ClientMessages.CLIENT_USERNAME,
                                         ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_key_id',
                     supported_messages=[ClientMessages.CLIENT_KEY_ID,
                                         ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_confirmation',
                     supported_messages=[ClientMessages.CLIENT_CONFIRMATION,
                                         ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_initial_client_ok',
                     supported_messages=[ClientMessages.CLIENT_OK,
                                         ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_client_ok',
                     supported_messages=[ClientMessages.CLIENT_OK,
                                         ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='wait_message',
                     supported_messages=[ClientMessages.CLIENT_MESSAGE,
                                         ClientMessages.CLIENT_RECHARGING]),
        MessageState(name='final'),
        MessageState(name='error'),
        MessageState(name='recharging',
                     supported_messages=ClientMessages.CLIENT_FULL_POWER)
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

        self.machine.add_transition('process_message',
                                    '*',
                                    'recharging',
                                    conditions=ClientMessages.CLIENT_RECHARGING.syntax_check,
                                    before=self._save_before_charging_state)
        self.machine.add_transition('process_message',
                                    'recharging',
                                    '=',
                                    conditions=ClientMessages.CLIENT_FULL_POWER.syntax_check,
                                    after=self._load_before_charging_state)
        self.machine.add_transition('process_message',
                                    'recharging',
                                    'error',
                                    before=lambda **kwargs:
                                    self._send_error(ServerMessages.SERVER_LOGIC_ERROR))

        self.machine.add_transition('process_message',
                                    'wait_username',
                                    'wait_key_id',
                                    conditions=ClientMessages.CLIENT_USERNAME.syntax_check,
                                    after=self._handle_correct_username)

        self.machine.add_transition('process_message',
                                    'wait_key_id',
                                    'wait_confirmation',
                                    conditions=ClientMessages.CLIENT_KEY_ID.logic_check,
                                    after=self._handle_correct_key_id)
        self.machine.add_transition('process_message',
                                    'wait_key_id',
                                    'error',
                                    conditions=ClientMessages.CLIENT_KEY_ID.syntax_check,
                                    before=lambda **kwargs: self._send_error(
                                        ServerMessages.SERVER_KEY_OUT_OF_RANGE_ERROR))

        self.machine.add_transition('process_message',
                                    'wait_confirmation',
                                    'wait_initial_client_ok',
                                    conditions=[ClientMessages.CLIENT_CONFIRMATION.syntax_check,
                                                self._check_client_hash],
                                    after=self._handle_correct_confirmation)
        self.machine.add_transition('process_message', 'wait_confirmation', 'error',
                                    conditions=ClientMessages.CLIENT_CONFIRMATION.syntax_check,
                                    before=lambda **kwargs:
                                    self._send_error(ServerMessages.SERVER_LOGIN_FAILED))

        self.machine.add_transition('process_message',
                                    ['wait_initial_client_ok', 'wait_client_ok'],
                                    'wait_message',
                                    conditions=ClientMessages.CLIENT_OK.unique_check,
                                    after=self._handle_client_ok_center)
        self.machine.add_transition('process_message',
                                    ['wait_initial_client_ok', 'wait_client_ok'],
                                    'wait_client_ok',
                                    conditions=ClientMessages.CLIENT_OK.syntax_check,
                                    after=self._handle_client_ok)

        self.machine.add_transition('process_message',
                                    'wait_message',
                                    'final',
                                    conditions=ClientMessages.CLIENT_MESSAGE.syntax_check,
                                    before=lambda **kwargs:
                                    self._send(ServerMessages.SERVER_LOGOUT))

        self.machine.add_transition('process_message',
                                    "*", 'error',
                                    before=lambda **kwargs:
                                    self._send_error(ServerMessages.SERVER_SYNTAX_ERROR))

    def _handle_correct_username(self, **kwargs):
        """
        The handle_correct_username function is called when the client sends a message
        with the correct username.
        The function parses out the robot's username from that message and stores it,
        and then sends a SERVER_KEY_REQUEST to request an encryption key.

        :return: A string of the robot's username
        """
        self.robot_username = ClientMessages.CLIENT_USERNAME.parse(**kwargs)
        self._send(ServerMessages.SERVER_KEY_REQUEST)

    def _handle_correct_key_id(self, **kwargs):
        """
        The handle_correct_key_id function is called when the client sends
        a message with the correct key_id.
        The function parses out the key_id from that message and stores.
        The function computes a username hash using compute_username_hash() and stores it.
        The function then sends a SERVER_CONFIRMATION message to the client.

        :return: The server_confirmation message
        """
        self.key_id = ClientMessages.CLIENT_KEY_ID.parse(**kwargs)
        self.username_hash = self._compute_username_hash(self.robot_username)
        self._send(ServerMessages.server_confirmation(self._compute_server_hash()))

    def _handle_correct_confirmation(self, **kwargs):
        """
        The handle_correct_confirmation function is called when the client sends
        a confirmation message after receiving the SERVER_CONFIRMATION message.
        The server responds with a SERVER_OK message and then sends a SERVER_MOVE message.
        """
        self._send(ServerMessages.SERVER_OK)
        self._send(ServerMessages.SERVER_MOVE)

    def _handle_client_ok(self, **kwargs):
        """
        The handle_client_ok function is called when the client sends
        a message of type CLIENT_OK after making a move.
        The function parses the message and updates the robot's position on the map. It then sends a
        message with an action that corresponds to what it should do next.
        """
        new_position = ClientMessages.CLIENT_OK.parse(**kwargs)
        self._send(ServerMessages.from_action(self.robot_map.update_position(new_position)))
        for observer in self.observers:
            observer.on_thread_event(MapUpdate(self.robot_map.get_map_state()))

    def _handle_client_ok_center(self, **kwargs):
        """
        The handle_client_ok_center function is called when the robot has reached
        the center of the map and sends a message of type CLIENT_OK.
        It updates its position on the map and sends a message to pick up the message.
        """
        new_position = ClientMessages.CLIENT_OK.parse(**kwargs)
        self.robot_map.update_position(new_position)
        for observer in self.observers:
            observer.on_thread_event(MapUpdate(self.robot_map.get_map_state()))
        self._send(ServerMessages.SERVER_PICK_UP)

    def on_enter_final(self, **kwargs):
        """
        Function called when the state machine enters the final state.
        """
        self._finish()

    def on_enter_error(self, **kwargs):
        """
        Function called when the state machine enters the error state.
        """
        self._finish()

    def _finish(self):
        """
        The finish function closes the connection and sets the stop flag.
        """
        self.conn.close()
        self.stop_flag = True
        logging.info("%s:%s finished, stopping thread.", *self.address)

    def _check_client_hash(self, **kwargs) -> bool:
        """
        The check_client_hash function is called when the client sends
        a message of type CLIENT_CONFIRMATION.
        The function parses out the client_hash from the message and
        compares it to the correct hash.

        :return: True if the client_hash is correct, False otherwise
        """
        client_hash = ClientMessages.CLIENT_CONFIRMATION.parse(**kwargs)
        right_hash = self._compute_client_hash()
        return client_hash == right_hash

    @staticmethod
    def _compute_username_hash(username: str) -> int:
        """
        The compute_username_hash function computes a hash value for the username.

        :param username: str: The username to hash.
        :return: Hash value for the username
        """
        return (sum(ord(c) for c in username) * 1000) % 65536

    def _compute_server_hash(self) -> int:
        """
        The compute_server_hash function returns a server hash value for
        the already stored username hash and key_id.

        :return: The hash of the username and key_id
        """
        return (self.username_hash + server_keys.get(self.key_id)) % 65536

    def _compute_client_hash(self) -> int:
        """
        The compute_client_hash function returns a client hash value for
        the already stored username hash and key_id.

        :return: The hash of the username and key_id
        """
        return (self.username_hash + client_keys.get(self.key_id)) % 65536

    def _save_before_charging_state(self, **kwargs):
        """
        This function saves the state before the robot enters the charging state.
        """
        self.before_charging_state = self.state

    def _load_before_charging_state(self, **kwargs):
        """
        This function loads the state the robot was in before it entered the charging state.
        """
        getattr(self, f"to_{self.before_charging_state}")(**kwargs)

    def on_enter_recharging(self, **kwargs):
        """
        This function is called when the robot enters the recharging state.
        It sets the timeout to TIMEOUT_RECHARGING.
        """
        self.conn.settimeout(TIMEOUT_RECHARGING)

    def on_exit_recharging(self, **kwargs):
        """
        This function is called when the robot exits the recharging state.
        It sets the timeout to the default TIMEOUT.
        """
        self.conn.settimeout(TIMEOUT)

    def add_observer(self, observer: RobotThreadObserver):
        """
        The add_observer function adds an observer to the list of observers.
        It also calls on_thread_event for that observer with a StateUpdate event.

        :param observer: RobotThreadObserver: An observer to add to the list of observers.
        """
        self.observers.append(observer)
        observer.on_thread_event(
            StateUpdate(self.state, self.state in ["final", "error"], self.error)
        )

    def on_state_change(self, **kwargs):
        """
        The on_state_change function is called when the state machine changes state.
        It calls on_thread_event for all observers with a StateUpdate event.
        """
        for observer in self.observers:
            observer.on_thread_event(
                StateUpdate(self.state, self.state in ["final", "error"], self.error)
            )

    def _send(self, bytestring: bytes):
        """
        The send function is used to send a message to the client.
        It takes in a bytestring and sends it over the socket connection.
        The function also logs what was sent, and notifies any observers that are listening.

        :param bytestring: bytes: The message to send to the client.
        """
        to_send = bytestring + self.end_sequence
        logging.info("%s:%s <<< %s", *self.address, to_send)
        self.conn.sendall(to_send)
        for observer in self.observers:
            observer.on_thread_event(
                MessageProcessed(self.message_in_process, bytestring, self.message_stack)
            )
        self.message_in_process = None

    def _send_error(self, error: bytes):
        """
        The send_error function is used to send an error message to the client.
        It takes in a bytestring and sends it over the socket connection.
        The function also stores the corresponding error message.

        :param error: bytes: The error message to send to the client.
        """
        self.error = ServerMessages.get_error_message(error)
        self._send(error)

    def run(self):
        """
        The run function is the main function of the thread. It handles all communication with
        the client, and it's where most of the logic happens. The run function has a while loop that
        continuously listens for messages from the client, and then processes them accordingly.
        """
        logging.info("(+) Thread working with address %s:%s", *self.address)
        self.conn.settimeout(TIMEOUT)
        try:
            while True:
                if self.stop_flag:
                    return
                text = self.conn.recv(1024)
                logging.info("%s:%s >>> %s", *self.address, text)
                if text == b"":
                    self.error = "Closed by client"
                    self.to_error()
                    return

                self.message_stack += text

                for observer in self.observers:
                    observer.on_thread_event(MessageStackUpdate(self.message_stack))

                if not ClientMessages.matches_message(self.message_stack, self.end_sequence) \
                        and self.machine.get_state(self.state) \
                        .exceeded_max_length(message=self.message_stack,
                                             end_sequence=self.end_sequence):
                    logging.info(
                        "%s:%s used all length with message: %s",
                        *self.address, self.message_stack
                    )
                    self._send(ServerMessages.SERVER_SYNTAX_ERROR)
                    self.error = "Exceeded length"
                    self.to_error()
                    self.conn.close()
                    return

                while ClientMessages.matches_message(
                        self.message_stack,
                        self.end_sequence):
                    message, rest = ClientMessages.parse_message(
                        self.message_stack,
                        self.end_sequence)
                    self.message_stack = rest
                    logging.info("%s:%s <=< %s", *self.address, message)
                    trimmed_message = message[:-len(self.end_sequence)]

                    self.message_in_process = trimmed_message
                    self.process_message(message=trimmed_message)
                    logging.info("%s:%s () State now: %s", *self.address, self.state)

        except socket.timeout:
            logging.info("%s:%s ! Timeout, disconnecting", *self.address)
            self.error = "Timeout"
            self.to_error()
            try:
                self.conn.close()
            except OSError:
                logging.warning("%s:%s ! Couldn't disconnect, possibly already did", *self.address)
            return
