import socket

import pytest
from _pytest.monkeypatch import MonkeyPatch

from archive.jim import JIMResponse, JIMMessage
from system.config import *
from system.errors import *

BYTE_TEST_DATA = b'{"action": "presence", "time": 1519377276, "type": "status", "user": ' \
                 b'{"account_name": "MOTHER_OF_DRAGON", "status": "Hello"}}'
WRONG_BYTE_TEST_DATA = b"asdasdfsdf"
DICT_TEST_DATA = {ACTION: PRESENCE, TIME: 1519377276, TYPE: STATUS, USER:
                  {ACCOUNT_NAME: 'MOTHER_OF_DRAGON', STATUS: "Hello"}}
WRONG_DICT_TEST_DATA = {12345:123456}


class SocketTest:
    """
    Класс заглушка для класса socket.socket
    """
    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM):
        self.data = BYTE_TEST_DATA
        self.m_resp = None

    def connect(self, address):
        if address[0] != 'localhost' or address[0] != '127.0.0.1':
            raise ConnectionRefusedError

    def send(self, message):
        self.data = message

    def recv(self, buffersize = 1024):
        self.m_resp = JIMResponse(self.data)
        self.m_resp.make_response_for_message()
        return self.m_resp.encoded_message


class WrongSocketTest(SocketTest):
    """
    Класс заглушка для сокета, закрывшего соединение
    """
    def recv(self, buffersize = 1024):
        return None


class TestMessage:
    """
    Проверка основных методов класса Message из модуля systems.jim
    """
    def setup(self):
        self.monkeypatch = MonkeyPatch()
        self.monkeypatch.setattr("socket.socket", SocketTest)
        self.sock = socket.socket()
        self.m = JIMMessage()

    def teardown(self):
        del self.sock
        del self.monkeypatch
        del self.m

    def test_encoding(self):
        self.m = JIMMessage(DICT_TEST_DATA)
        assert BYTE_TEST_DATA == self.m.encoded_message

    def test_decoding(self):
        self.m = JIMMessage(BYTE_TEST_DATA)
        assert DICT_TEST_DATA == self.m.dict_message

    def test_decoding_bad_message(self):
        with pytest.raises(DecodedMessageError):
            JIMMessage(WRONG_BYTE_TEST_DATA)

    def test_encoding_bad_message(self):
        with pytest.raises(TypeError):
            JIMMessage(123)

    def test_wrong_message_type(self):
        with pytest.raises(TypeError):
            JIMMessage(123)

    def test_send(self):
        self.m.create_presence_message()
        self.m.send_message(self.sock)
        assert self.sock.data == self.m.encoded_message

    def test_receive(self):
        self.m.rcv_message(self.sock)
        assert self.m.dict_message.get(RESPONSE) == OK

    def test_bad_receive(self):
        self.monkeypatch.setattr('socket.socket', WrongSocketTest)
        self.sock = socket.socket()
        with pytest.raises(ClosedSocketError):
            self.m.rcv_message(self.sock)

    def test_send_recv_message(self):
        self.m.encoded_message = BYTE_TEST_DATA
        self.m.send_rcv_message(self.sock)
        assert self.sock.data == BYTE_TEST_DATA
        assert self.m.dict_message.get(RESPONSE) == OK







