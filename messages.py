import re
from robot_map import Action


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


class ClientMessages:

    def __init__(self, end_sequence, arg_name):
        self.end_sequence = end_sequence
        self.arg_name = arg_name

    def _re_check(self, re_str, add_end=True, full_match=True, **kwargs):
        if self.arg_name not in kwargs.keys():
            raise NameError(f'"{self.arg_name}" not in kwargs')
        if full_match:
            return re.fullmatch(re_str + (self.end_sequence if add_end else b''), kwargs.get(self.arg_name)) is not None
        return re.match(re_str + (self.end_sequence if add_end else b''), kwargs.get(self.arg_name)) is not None

    def username(self, **kwargs):
        return self._re_check(b".{1,20}", **kwargs) \
            and not self._re_check(self.end_sequence + b".", add_end=False, full_match=False, **kwargs)

    def key_id(self, **kwargs):
        return self._re_check(b"[01234]", **kwargs)

    def key_id_syntax(self, **kwargs):
        return self._re_check(b"(-|\d)?\d?\d", **kwargs)

    def confirmation_syntax(self, **kwargs):
        return self._re_check(b"\d{1,5}", **kwargs)

    def ok_center(self, **kwargs):
        return self._re_check(b"OK 0 0", **kwargs)

    def ok(self, **kwargs):
        return self._re_check(b"OK -?\d{1,4} -?\d{1,4}", **kwargs) and self._re_check(b".{1,12}", **kwargs)

    def message(self, **kwargs):
        return self._re_check(b".{1,98}", **kwargs) \
            and not self._re_check(self.end_sequence + b".", add_end=False, full_match=False, **kwargs)

    def parse_key(self, **kwargs):
        res = re.fullmatch(b"([01234])" + self.end_sequence, kwargs.get(self.arg_name))
        return int(res.group(1))

    def parse_username(self, **kwargs):
        res = re.fullmatch(b"(.{1,20})" + self.end_sequence, kwargs.get(self.arg_name))
        return res.group(1).decode()

    def parse_confirmation(self, **kwargs):
        res = re.fullmatch(b"(\d{1,5})" + self.end_sequence, kwargs.get(self.arg_name))
        return int(res.group(1))

    def parse_position(self, **kwargs):
        res = re.fullmatch(b"OK (-?\d{1,4}) (-?\d{1,4})" + self.end_sequence, kwargs.get(self.arg_name))
        return int(res.group(1)), int(res.group(2))
