import socket
import time

from robot_server.server import RobotServer
import pytest
import threading

HOST, PORT = "127.0.0.1", 61112


@pytest.fixture(scope="module", autouse=True)
def server():
    server = RobotServer(host=HOST, port=PORT)
    thread = threading.Thread(target=server.start)
    thread.daemon = True
    thread.start()
    yield
    server.stop()


@pytest.fixture(scope="function")
def client(server):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    yield s
    s.close()


@pytest.fixture(scope="function")
def authorized_client(client):
    client.sendall(b"Oompa Loompa\a\b")
    assert client.recv(1024) == b"107 KEY REQUEST\a\b"
    client.sendall(b"0\a\b")
    assert client.recv(1024) == b"64907\a\b"
    client.sendall(b"8389\a\b")
    time.sleep(0.1)
    assert client.recv(1024) == b"200 OK\a\b102 MOVE\a\b"
    return client


def test_example(client):
    client.sendall(b"Oompa Loompa\a\b")
    assert client.recv(1024) == b"107 KEY REQUEST\a\b"
    client.sendall(b"0\a\b")
    assert client.recv(1024) == b"64907\a\b"
    client.sendall(b"8389\a\b")
    time.sleep(0.1)
    assert client.recv(1024) == b"200 OK\a\b102 MOVE\a\b"
    client.sendall(b"OK 0 -1\a\b")
    assert client.recv(1024) == b"102 MOVE\a\b"
    client.sendall(b"OK 0 0\a\b")
    assert client.recv(1024) == b"105 GET MESSAGE\a\b"
    client.sendall(b"Tajny vzkaz.\a\b")
    assert client.recv(1024) == b"106 LOGOUT\a\b"


def test_example_2(authorized_client):
    authorized_client.sendall(b"OK 0 1\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"OK 0 2\a\b")
    assert authorized_client.recv(1024) == b"103 TURN LEFT\a\b"
    authorized_client.sendall(b"OK 0 2\a\b")
    assert authorized_client.recv(1024) == b"103 TURN LEFT\a\b"
    authorized_client.sendall(b"OK 0 2\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"OK 0 1\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"OK 0 0\a\b")
    assert authorized_client.recv(1024) == b"105 GET MESSAGE\a\b"
    authorized_client.sendall(b"Tajny vzkaz.\a\b")
    assert authorized_client.recv(1024) == b"106 LOGOUT\a\b"


def test_example_obstacle(authorized_client):
    authorized_client.sendall(b"OK -1 -1\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"OK -1 -1\a\b")
    assert authorized_client.recv(1024) == b"104 TURN RIGHT\a\b"
    authorized_client.sendall(b"OK -1 -1\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"OK 0 -1\a\b")
    assert authorized_client.recv(1024) == b"103 TURN LEFT\a\b"
    authorized_client.sendall(b"OK 0 -1\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"OK 0 0\a\b")
    assert authorized_client.recv(1024) == b"105 GET MESSAGE\a\b"
    authorized_client.sendall(b"Tajny vzkaz.\a\b")
    assert authorized_client.recv(1024) == b"106 LOGOUT\a\b"


def test_example_recharging(authorized_client):
    authorized_client.sendall(b"OK 0 -2\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"RECHARGING\a\b")
    time.sleep(2)
    authorized_client.sendall(b"FULL POWER\a\b")
    authorized_client.sendall(b"OK 0 -1\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"OK 0 0\a\b")
    assert authorized_client.recv(1024) == b"105 GET MESSAGE\a\b"
    authorized_client.sendall(b"Tajny vzkaz.\a\b")
    assert authorized_client.recv(1024) == b"106 LOGOUT\a\b"


def test_error_1(client):
    client.sendall(b"Oompa Loompa\a\b")
    assert client.recv(1024) == b"107 KEY REQUEST\a\b"
    client.sendall(b"10\a\b")
    assert client.recv(1024) == b"303 KEY OUT OF RANGE\a\b"


def test_error_2(client):
    client.sendall(b"Oompa Loompa\a\b")
    assert client.recv(1024) == b"107 KEY REQUEST\a\b"
    client.sendall(b"-1\a\b")
    assert client.recv(1024) == b"303 KEY OUT OF RANGE\a\b"


def test_error_3(client):
    client.sendall(b"\a\b")
    assert client.recv(1024) == b"301 SYNTAX ERROR\a\b"


def test_timeout(authorized_client):
    time.sleep(1.1)
    assert authorized_client.recv(1024) == b""


def test_recharging_timeout(authorized_client):
    authorized_client.sendall(b"OK 0 -2\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"RECHARGING\a\b")
    time.sleep(5.1)
    assert authorized_client.recv(1024) == b""


def test_logic_error(authorized_client):
    authorized_client.sendall(b"OK 0 -2\a\b")
    assert authorized_client.recv(1024) == b"102 MOVE\a\b"
    authorized_client.sendall(b"RECHARGING\a\b")
    time.sleep(0.1)
    authorized_client.sendall(b"OK 0 -1\a\b")
    assert authorized_client.recv(1024) == b"302 LOGIC ERROR\a\b"


def test_syntax_length_error(authorized_client):
    authorized_client.sendall(b"OK ")
    authorized_client.sendall(b"4 ")
    authorized_client.sendall(b"4 ")
    authorized_client.sendall(b"2124124 ")
    assert authorized_client.recv(1024) == b"301 SYNTAX ERROR\a\b"
