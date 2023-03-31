import re
from robot_map import Action
from dataclasses import dataclass


class ServerMessages:
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

    @staticmethod
    def server_confirmation(server_hash: int) -> bytes:
        return str(server_hash).encode()

    @classmethod
    def from_action(cls, action: Action):
        return {
            Action.MOVE: cls.SERVER_MOVE,
            Action.TURN_RIGHT: cls.SERVER_TURN_RIGHT,
            Action.TURN_LEFT: cls.SERVER_TURN_LEFT
        }.get(action)


arg_name = "message"


@dataclass
class RegexCheck:
    regex: bytes
    unless: bool = False
    full_match: bool = True
    end_sequence: bytes = b"\a\b"

    def test(self, **kwargs):
        if arg_name not in kwargs.keys():
            raise NameError(f'"{arg_name}" not in kwargs')

        if self.full_match:
            res = re.fullmatch(self.regex, kwargs.get(arg_name))
        else:
            res = re.match(self.regex, kwargs.get(arg_name))

        return (res is not None) ^ self.unless

    def parse(self, cast_type=None, **kwargs):
        if not self.test(**kwargs):
            raise ValueError("Cannot parse when the check isn't fulfilled")
        match = re.match(self.regex, kwargs.get(arg_name))
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

    def __init__(self, max_len=None, syntax_checks=None, logic_checks=None, unique_checks=None, parse_cast=None):
        syntax_checks = syntax_checks if syntax_checks is not None else []
        logic_checks = logic_checks if logic_checks is not None else []
        unique_checks = unique_checks if unique_checks is not None else []
        self._logic_checks: list[RegexCheck] = logic_checks if isinstance(logic_checks, list) else [logic_checks]
        self._syntax_checks: list[RegexCheck] = syntax_checks if isinstance(syntax_checks, list) else [syntax_checks]
        self._unique_checks: list[RegexCheck] = unique_checks if isinstance(unique_checks, list) else [unique_checks]
        self.max_len = max_len
        self.parse_cast = parse_cast

    def used_length(self, **kwargs):
        if self.max_len is None:
            return False
        return not RegexCheck(b".{1," + str(self.max_len-1).encode() + b"}").test(**kwargs)

    def length_check(self, **kwargs):
        if self.max_len is None:
            return True
        return RegexCheck(b".{1," + str(self.max_len).encode() + b"}").test(**kwargs)

    def syntax_check(self, **kwargs):
        return self.length_check(**kwargs) and all(c.test(**kwargs) for c in self._syntax_checks)

    def logic_check(self, **kwargs):
        return self.syntax_check(**kwargs) and all(c.test(**kwargs) for c in self._logic_checks)

    def unique_check(self, **kwargs):
        return self.logic_check(**kwargs) and all(c.test(**kwargs) for c in self._unique_checks)

    def parse(self, **kwargs):
        if len(self._syntax_checks) == 0:
            return RegexCheck(b".*").parse(cast_type=self.parse_cast, **kwargs)
        if len(self._syntax_checks) > 1:
            raise ValueError("Can't parse with more than one syntax check")
        return self._syntax_checks[0].parse(cast_type=self.parse_cast, **kwargs)


class ClientMessages:
    CLIENT_USERNAME = ClientMessage(18, parse_cast=str)
    CLIENT_KEY_ID = ClientMessage(3, syntax_checks=RegexCheck(b"-?\d+"),
                                  logic_checks=RegexCheck(b"[01234]"), parse_cast=int)
    CLIENT_CONFIRMATION = ClientMessage(5, syntax_checks=RegexCheck(b"\d{1,5}"), parse_cast=int)
    CLIENT_OK = ClientMessage(10, syntax_checks=RegexCheck(b"OK (-?\d{1,4}) (-?\d{1,4})"),
                              unique_checks=RegexCheck(b"OK 0 0"), parse_cast=int)
    CLIENT_MESSAGE = ClientMessage(98)

    @staticmethod
    def matches_message(message: bytes, end_sequence: bytes):
        return re.match(b"^.*?" + end_sequence, message) is not None

    @staticmethod
    def parse_message(message: bytes, end_sequence: bytes):
        match = re.match(b"^.*?" + end_sequence, message)
        return match.group(0), message[match.end():]
