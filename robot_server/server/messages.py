"""
This module contains all the messages that are sent between the server and the client.
"""

import re
from typing import Optional
from dataclasses import dataclass

from .map import Action


class ServerMessages:
    """
    Class containing all the messages that are sent by the server.
    """
    SERVER_KEY_REQUEST = b"107 KEY REQUEST"
    SERVER_OK = b"200 OK"
    SERVER_KEY_OUT_OF_RANGE_ERROR = b"303 KEY OUT OF RANGE"
    SERVER_SYNTAX_ERROR = b"301 SYNTAX ERROR"
    SERVER_LOGIN_FAILED = b"300 LOGIN FAILED"
    SERVER_MOVE = b"102 MOVE"
    SERVER_TURN_LEFT = b"103 TURN LEFT"
    SERVER_TURN_RIGHT = b"104 TURN RIGHT"
    SERVER_PICK_UP = b"105 GET MESSAGE"
    SERVER_LOGOUT = b"106 LOGOUT"
    SERVER_LOGIC_ERROR = b"302 LOGIC ERROR"

    @staticmethod
    def server_confirmation(server_hash: int) -> bytes:
        """
        Returns the server confirmation message for the given server hash.

        :param server_hash: The server hash.
        :return: The server confirmation message.
        """
        return str(server_hash).encode()

    @classmethod
    def from_action(cls, action: Action):
        """
        Returns the server message for the given action.

        :param action: The action.
        :return: The server message.
        """
        return {
            Action.MOVE: cls.SERVER_MOVE,
            Action.TURN_RIGHT: cls.SERVER_TURN_RIGHT,
            Action.TURN_LEFT: cls.SERVER_TURN_LEFT
        }.get(action)

    @classmethod
    def get_error_message(cls, message: bytes) -> Optional[str]:
        """
        Returns the readable error message for the given server error message.

        :param message: The error server message.
        :return: The error message in a readable format.
        """
        return {
            cls.SERVER_KEY_OUT_OF_RANGE_ERROR: "Key out of range",
            cls.SERVER_SYNTAX_ERROR: "Syntax error",
            cls.SERVER_LOGIN_FAILED: "Login failed",
            cls.SERVER_LOGIC_ERROR: "Logic error"
        }.get(message, None)


ARG_NAME = "message"


@dataclass
class RegexCheck:
    """
    Class for a regex check on messages.

    :param regex: The regex to check.
    :param unless: Whether the check should be inverted.
    :param full_match: If False, test string could contain additional characters at the end
    """
    regex: bytes
    unless: bool = False
    full_match: bool = True

    def test(self, **kwargs):
        """
        Returns whether the message matches the regex.

        :return: Whether the message matches the regex.
        """
        if ARG_NAME not in kwargs:
            raise NameError(f'"{ARG_NAME}" not in kwargs')

        if self.full_match:
            res = re.fullmatch(self.regex, kwargs.get(ARG_NAME))
        else:
            res = re.match(self.regex, kwargs.get(ARG_NAME))

        return (res is not None) ^ self.unless

    def parse(self, cast_type=None, **kwargs):
        """
        Returns the parsed message (the first group of the regex).
        There should be exactly one group in the regex.

        :param cast_type: The type to cast the result to.
        :return: The parsed message.
        """
        if not self.test(**kwargs):
            raise ValueError("Cannot parse when the check isn't fulfilled")
        match = re.match(self.regex, kwargs.get(ARG_NAME))
        res = match.groups()
        if len(res) == 0:
            res = match.group()

            if not cast_type:
                return res
            if cast_type == str:
                return res.decode()
            return cast_type(res)

        if not cast_type:
            return res
        if cast_type == str:
            return tuple((x.decode() for x in res))
        return tuple((cast_type(x) for x in res))


class ClientMessage:
    """
    Class for a client message.
    """

    # pylint: disable=too-many-arguments
    def __init__(self,
                 max_len=None,
                 syntax_checks=None,
                 logic_checks=None,
                 unique_checks=None,
                 parse_cast=None):
        """
        :param max_len: The maximum length of the message.
        :param syntax_checks: The syntax checks to perform on the message.
        :param logic_checks: The logic checks to perform on the message.
        :param unique_checks: The unique checks to perform on the message.
        :param parse_cast: The type to cast the parsed message to.
        """
        syntax_checks = syntax_checks if syntax_checks is not None else []
        logic_checks = logic_checks if logic_checks is not None else []
        unique_checks = unique_checks if unique_checks is not None else []
        self._logic_checks: list[RegexCheck] = \
            logic_checks if isinstance(logic_checks, list) else [logic_checks]
        self._syntax_checks: list[RegexCheck] = \
            syntax_checks if isinstance(syntax_checks, list) else [syntax_checks]
        self._unique_checks: list[RegexCheck] = \
            unique_checks if isinstance(unique_checks, list) else [unique_checks]
        self.max_len = max_len
        self.parse_cast = parse_cast

    def length_check(self, **kwargs):
        """
        Returns whether the message is of the correct length.

        :return: Whether the message is of the correct length.
        """
        if self.max_len is None:
            return True
        return RegexCheck(br".{1," + str(self.max_len).encode() + br"}").test(**kwargs)

    def syntax_check(self, **kwargs):
        """
        Returns whether the message passes the syntax checks.
        Also checks the length of the message.

        :return: Whether the message passes the syntax checks.
        """
        return self.length_check(**kwargs) and all(c.test(**kwargs) for c in self._syntax_checks)

    def logic_check(self, **kwargs):
        """
        Returns whether the message passes the logic checks.
        Also checks the syntax of the message.

        :return: Whether the message passes the logic checks.
        """
        return self.syntax_check(**kwargs) and all(c.test(**kwargs) for c in self._logic_checks)

    def unique_check(self, **kwargs):
        """
        Returns whether the message passes the unique checks.
        Also checks if the values in the message pass the logic checks.

        :return: Whether the message passes the unique checks.
        """
        return self.logic_check(**kwargs) and all(c.test(**kwargs) for c in self._unique_checks)

    def parse(self, **kwargs):
        """
        Returns the parsed message.

        :return: The parsed message.
        """
        if len(self._syntax_checks) == 0:
            return RegexCheck(br".*").parse(cast_type=self.parse_cast, **kwargs)
        if len(self._syntax_checks) > 1:
            raise ValueError("Can't parse with more than one syntax check")
        return self._syntax_checks[0].parse(cast_type=self.parse_cast, **kwargs)


class ClientMessages:
    """
    Class for all client messages.
    """
    CLIENT_USERNAME = ClientMessage(18, parse_cast=str)
    CLIENT_KEY_ID = ClientMessage(3, syntax_checks=RegexCheck(br"-?\d+"),
                                  logic_checks=RegexCheck(br"[01234]"), parse_cast=int)
    CLIENT_CONFIRMATION = ClientMessage(5, syntax_checks=RegexCheck(br"\d{1,5}"), parse_cast=int)
    CLIENT_OK = ClientMessage(10, syntax_checks=RegexCheck(br"OK (-?\d{1,4}) (-?\d{1,4})"),
                              unique_checks=RegexCheck(br"OK 0 0"), parse_cast=int)
    CLIENT_MESSAGE = ClientMessage(98)
    CLIENT_RECHARGING = ClientMessage(10, syntax_checks=RegexCheck(br"RECHARGING"))
    CLIENT_FULL_POWER = ClientMessage(10, syntax_checks=RegexCheck(br"FULL POWER"))

    @staticmethod
    def matches_message(message: bytes, end_sequence: bytes):
        """
        Returns whether a bytestring matches the message type.
        The message type must end with the end sequence.

        :param message: The bytestring to check.
        :param end_sequence: The end sequence of the message type.
        :return: Whether the bytestring matches the message type.
        """
        return re.match(br"^.*?" + end_sequence, message) is not None

    @staticmethod
    def parse_message(message: bytes, end_sequence: bytes) -> tuple[bytes, bytes]:
        """
        Returns the parsed message and the rest of the bytestring.

        :param message: The bytestring to parse.
        :param end_sequence: The end sequence of the message type.
        :return: The parsed message and the rest of the bytestring.
        """
        match = re.match(br"^.*?" + end_sequence, message)
        return match.group(0), message[match.end():]
