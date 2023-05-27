import pytest

from robot_server.server.messages import ServerMessages, \
    ClientMessage, ClientMessages, ARG_NAME, RegexCheck
from robot_server.server.map import Action


def test_server_confirmation():
    assert ServerMessages.server_confirmation(123) == b"123"
    assert ServerMessages.server_confirmation(456) == b"456"
    assert ServerMessages.server_confirmation(789) == b"789"


def test_action():
    assert ServerMessages.from_action(Action.MOVE) \
           == ServerMessages.SERVER_MOVE
    assert ServerMessages.from_action(Action.TURN_RIGHT) \
           == ServerMessages.SERVER_TURN_RIGHT
    assert ServerMessages.from_action(Action.TURN_LEFT) \
           == ServerMessages.SERVER_TURN_LEFT


def test_get_error_message():
    assert isinstance(ServerMessages.
                      get_error_message(ServerMessages.
                                        SERVER_KEY_OUT_OF_RANGE_ERROR),
                      str)
    assert ServerMessages.get_error_message(
        ServerMessages.SERVER_OK) is None


@pytest.mark.parametrize(
    'regex, unless, full, test, expected',
    [
        (br"\d{1,3}", False, True, b"123", True),
        (br"\d{1,3}", False, True, b"1234", False),
        (br"\d{1,3}", False, False, b"1234", True),
        (br"\d{1,3}", True, True, b"123", False),
        (br"\d{1,3}", True, True, b"1234", True),
        (br"\d{1,3}", True, False, b"1234", False),
    ])
def test_regex_check(regex, unless, full, test, expected):
    assert RegexCheck(regex, unless, full) \
               .test(**{ARG_NAME: test}) == expected


@pytest.mark.parametrize(
    'regex, unless, full, test, cast, expected',
    [
        (br"(\d{1,3})", False, True, b"123", str, ("123",)),
        (br"OK (\d{1,3}) (\d)", False, True, b"OK 123 4", str, ("123", "4")),
        (br"OK (\d{1,3}) (\d)", False, True, b"OK 123 4", int, (123, 4)),
        (br"OK \d{1,3}", False, True, b"OK 123", str, "OK 123"),
        (br"OK \d{1,3} \d", False, True, b"OK 123 4", str, "OK 123 4"),
        (br"\d{1,3}", False, False, b"123 4", int, 123),
        (br"OK \d{1,3} \d", False, True, b"OK 123 4", None, b"OK 123 4"),
        (br"OK (\d{1,3}) (\d)", False, True, b"OK 123 4", None, (b"123", b"4")),
    ])
def test_regex_parse(regex, unless, full, test, cast, expected):
    assert RegexCheck(regex, unless, full) \
               .parse(**{ARG_NAME: test}, cast_type=cast) == expected


def test_regex_errors():
    with pytest.raises(NameError):
        RegexCheck(br"(\d{1,3})").test()

    reg = RegexCheck(br"(\d{1,3})")
    assert reg.test(**{ARG_NAME: b"123"})
    with pytest.raises(NameError):
        reg.parse(cast_type=int)
    assert not reg.test(**{ARG_NAME: b"1234"})
    with pytest.raises(ValueError):
        reg.parse(cast_type=int, **{ARG_NAME: b"1234"})


def test_client_message():
    mes = ClientMessage(
        max_len=10,
        syntax_checks=RegexCheck(br"OK (-?\d{1,4}) (-?\d{1,4})"),
        unique_checks=RegexCheck(br"OK 0 0"),
        parse_cast=int)
    assert mes.syntax_check(**{ARG_NAME: b"OK 123 456"})
    assert mes.syntax_check(**{ARG_NAME: b"OK 0 0"})
    assert not mes.syntax_check(**{ARG_NAME: b"OK 123.1 456"})
    assert not mes.unique_check(**{ARG_NAME: b"OK 0.0 0"})
    assert mes.unique_check(**{ARG_NAME: b"OK 0 0"})
    assert mes.parse(**{ARG_NAME: b"OK 123 456"}) == (123, 456)
    assert mes.parse(**{ARG_NAME: b"OK 0 0"}) == (0, 0)


def test_parse_no_checks():
    mes = ClientMessage(max_len=10)
    assert mes.syntax_check(**{ARG_NAME: b"OK 123 456"})
    assert mes.parse(**{ARG_NAME: b"OK 123 456"}) == b"OK 123 456"


def test_parse_list_error():
    mes = ClientMessage(
        max_len=10,
        syntax_checks=[RegexCheck(br"OK (-?\d{1,4}) (-?\d{1,4})"),
                       RegexCheck(br"OK (.)+")],
        parse_cast=int)
    assert mes.syntax_check(**{ARG_NAME: b"OK 123 456"})
    with pytest.raises(ValueError):
        mes.parse(**{ARG_NAME: b"OK 123 456"})


def test_message_static():
    assert ClientMessages.matches_message(message=b"OK 123 456",
                                          end_sequence=b"OK")
    assert ClientMessages.matches_message(message=b"OK 123 456",
                                          end_sequence=b"OK 123 456")
    assert ClientMessages.matches_message(message=b"OK 123 456\a\b",
                                          end_sequence=b"\a\b")
    assert not ClientMessages.matches_message(message=b"OK 123 456\a\b",
                                              end_sequence=b"\a\b\1")
    assert ClientMessages.parse_message(message=b"OK 123 456\a\b",
                                        end_sequence=b"\a\b") == \
           (b"OK 123 456\a\b", b"")
    assert ClientMessages.parse_message(message=b"XXX XXX\aYY YY YY\aZZ ZZ",
                                        end_sequence=b"\a") == \
           (b"XXX XXX\a", b"YY YY YY\aZZ ZZ")
    assert ClientMessages.parse_message(message=b"XXX XXX\aYY YY YY\aZZ ZZ",
                                        end_sequence=b"\aYY") == \
           (b"XXX XXX\aYY", b" YY YY\aZZ ZZ")
