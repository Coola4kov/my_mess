import socket
import time
import json
import sys

from .errors import DecodedMessageError, ClosedSocketError
from .config import *


def open_client_socket(host, port):
    """
    Создаёт экземпляр класса socket для клиентского приложения
    :param host: имя хоста или ip адрес
    :param port: порт
    :return: сокет, с установленным соединением до определенного хоста
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except ConnectionRefusedError:

        raise ConnectionRefusedError("Соединение по {}:{} не возможно".format(host, port))
    return sock


def open_server_socket(int_add, port, connections=5, timeout=5):
    """
    Создаёт экземпляр класса socket для серверного приложения, привязывается к заданному порту и начинает слушать
    на наличие соединений.
    :param int_add: адрес интерфейса, который должен прослушиваться
    :param port: порт
    :param connections: количество одновременных соединений
    :param timeout: таймаут в ожидании нового соединения
    :return:
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((int_add, port))
    except socket.gaierror:
        print("Введёного адреса интерфейса не существует")
        sys.exit(1)
    sock.settimeout(timeout)
    sock.listen(connections)
    return sock


def find_cli_key_and_argument(key_, default):
    """
    Возвращает значение следующее за ключём, иначе устанавливает значение переданное как default

    $ python3 messenger_server.py -p 778 -a 127.0.0.1
    >>find_cli_key_and_argument(-p, 7777)
    778

    $ python3 messenger_server.py -p abc -a 127.0.0.1
    >>find_cli_key_and_argument(-p, 7777)
    Введёное значение порта не верно

    $ python3 messenger_server.py -a 127.0.0.1
    >>find_cli_key_and_argument(-p, 7777)
    7777
    """
    if key_ in sys.argv:
        try:
            argument = sys.argv[sys.argv.index(key_) + 1]
        except IndexError:
            argument = default
    else:
        argument = default
    return argument


# TODO добавить socket в качестве аргумента экземпляра класса
class Message:
    """
    Класс для обработки сообщений для работы мессенджера JIM
    Если экземпляру класса будет передано новое сообщение, старое сообщение будет удалено.
    В один момент, класс работает с одним сообщением.
    """

    def __init__(self, message=None, encoding='ascii'):
        """
        При инициализации метода класса, в зависимости от типа сообщение оно будет приготовленно к отправке,
        предварительно перекодировавшись в bytes, либо в dict

        Если сообщение не передаётся, создаются пустые сообщение с byte и dict
        """
        self.encoding = encoding

        if message:
            if type(message) == bytes:
                self.encoded_message = message
                self.dict_message = self.decode_message()
            elif type(message) == dict:
                self.dict_message = message
                self.encoded_message = self.encode_message()
            else:
                raise TypeError("Введённый тип не поддерживается, должно быть bytes или dict")
        else:
            self.encoded_message = b""
            self.dict_message = {}

    def __str__(self):
        """
        Возвращает сообщение в виде словаря
        >>m = Message({"foo":"bar"})
        >>print(m)
        {"foo":"bar"}
        """
        return str(self.dict_message)

    def decode_message(self):
        """
        Декодирует переданное сообщение из bytes в JSON, после этого в dict.
        Декодирование осуществляется с заданной кодировкой
        """
        # print('Кодированное сообщение', self.encoded_message)
        json_message = self.encoded_message.decode(self.encoding)
        try:
            decoded_message = json.loads(json_message)
        except json.decoder.JSONDecodeError:
            raise DecodedMessageError
        self.dict_message = decoded_message
        return decoded_message

    def encode_message(self):
        """
        Кодирует сообщение с заданной кодиеровкой, в начале в JSON, после этого в bytes

        """
        if type(self.dict_message) != dict:
            raise TypeError('Данное сообщение должно быть type dict \n'.format(self.dict_message))
        json_message = json.dumps(self.dict_message)
        raw_byte_message = json_message.encode(self.encoding)
        self.encoded_message = raw_byte_message
        return raw_byte_message

    def rcv_message(self, sock):
        """
        Получаем ответ от сервера, если он не ответил, возвратится пустая строка
        """
        self.encoded_message = sock.recv(1024)
        if not self.encoded_message:
            raise ClosedSocketError(sock)
        # print(self.encoded_message)
        self.decode_message()
        return self.dict_message

    def send_message(self, sock):
        """
        Отправка сообшения
        """
        if not self.encoded_message:
            self.encode_message()
        try:
            sock.send(self.encoded_message)
        except ConnectionAbortedError:
            print('Конечная сторона закрыла соединение, сообщение не отправлено')

    def send_rcv_message(self, sock):
        self.send_message(sock)
        return self.rcv_message(sock)

    def clean_buffer(self):
        self.encoded_message = b""
        self.dict_message = {}


class JIMMessage(Message):
    @staticmethod
    def _create_message(action=PRESENCE, time_included=True, **kwargs):
        """
        Метод создаёт сообщение на основе переданного ей параметров в виде dict и типа действия и
        дополняет его timestamp
        """
        message = {ACTION: action}
        if time_included:
            message.update({TIME: int(time.time())})
        message.update(kwargs)
        return message

    def create_presence_message(self, account="basic_user", status="Yep, I'm here!"):
        """
        Метод оздаёт presence сообщение и присваивает значение self.message
        из параметров на вход он принимает статус сообщение и имя пользователя
        """
        user = {ACCOUNT_NAME: account, STATUS: status}
        body = {TYPE: 'status', USER: user}
        self.dict_message = self._create_message(action=PRESENCE, **body)
        return self._end_of_creating()

    def create_probe_message(self):
        self.dict_message = self._create_message(action=PROBE, time_included=True)
        return self._end_of_creating()

    def create_msg_message(self, room=False, to='jim_user', from_='basic_user', message='Hello World'):
        """
        Метод создаёт сообщение типа msg
        :param to: str type, кому передаётся сообщение
        :param from_: str type, от кого передаётся сообщение
        :param message: str type, само сообщение
        :return: dict type, сообщение сформированное dict сообщение для протокола JSON
        """
        if room:
            to = '#' + to
        body = {TO: to, FROM: from_, ENCODING: self.encoding, MESSAGE: message}
        self.dict_message = self._create_message(MSG, **body)
        return self._end_of_creating()

    def create_get_contact_message(self):
        self.dict_message = self._create_message(GET_CONTACTS)
        return self._end_of_creating()

    def create_change_contact_message(self, username='basic_user', add=True):
        body = {USER_ID: username}
        if add:
            action = ADD_CONTACT
        else:
            action = DEL_CONTACT
        self.dict_message = self._create_message(action, **body)
        return self._end_of_creating()

    def create_chat_message(self, room_name='basic_room', join=True):
        body = {ROOM: room_name}
        if join:
            action = JOIN
        else:
            action = LEAVE
        self.dict_message = self._create_message(action=action, **body)
        return self._end_of_creating()

    def create_server_contact_list(self, contact_name='basic_user'):
        body = {USER_ID: contact_name}
        self.dict_message = self._create_message(CONTACT_LIST, **body, time_included=False)
        return self._end_of_creating()

    def create_auth_message(self, account_name='basic_user', password=''):
        user = {ACCOUNT_NAME: account_name, PASSWORD: password}
        body = {USER: user}
        self.dict_message = self._create_message(AUTH, True, **body)
        return self._end_of_creating()

    def _end_of_creating(self):
        self.encode_message()
        return self.dict_message


class JIMResponse(Message):
    def get_message_action(self):
        """
        Возвращает тип действия, запрашиваемого клиентом
        :return:
        """
        check_methods = {PRESENCE: self._presence_check, MSG: self._msg_check, GET_CONTACTS: self._get_contacts_check,
                         ADD_CONTACT: self._add_contact_check, DEL_CONTACT: self._del_contact_check,
                         JOIN: self._join_check, LEAVE: self._leave_check, AUTH: self._auth_check}
        # Метод для осущеснтвления проверки достаём из типа ACTION, пришедшего в сообщении
        method = check_methods.get(self.dict_message.get(ACTION))
        if method:
            action = method()
        else:
            action = None
        return action

    def _auth_check(self):
        if self.dict_message.get(ACTION) == AUTH \
                and TIME in self.dict_message \
                and USER in self.dict_message:
            action = AUTH
        else:
            action = 0
        return action

    def _join_check(self):
        if self.dict_message.get(ACTION) == JOIN \
                and TIME in self.dict_message \
                and ROOM in self.dict_message:
            action = JOIN
        else:
            action = None
        return action

    def _leave_check(self):
        if self.dict_message.get(ACTION) == LEAVE \
                and TIME in self.dict_message \
                and ROOM in self.dict_message:
            action = LEAVE
        else:
            action = None
        return action

    def _del_contact_check(self):
        if self.dict_message.get(ACTION) == DEL_CONTACT \
                and USER_ID in self.dict_message \
                and TIME in self.dict_message:
            action = DEL_CONTACT
        else:
            action = None
        return action

    def _add_contact_check(self):
        if self.dict_message.get(ACTION) == ADD_CONTACT \
                and USER_ID in self.dict_message \
                and TIME in self.dict_message:
            action = ADD_CONTACT
        else:
            action = None
        return action

    def _get_contacts_check(self):
        if self.dict_message.get(ACTION) == GET_CONTACTS \
               and TIME in self.dict_message:
            action = GET_CONTACTS
        else:
            action = None
        return action

    def _presence_check(self):
        """
        Проверка на правильный формат presence сообщения
        :return: string, тип действия в сообщении или None если сообщение не правильное
        """
        if self.dict_message.get(ACTION) == PRESENCE \
               and TIME in self.dict_message \
               and USER in self.dict_message \
               and TYPE in self.dict_message \
               and ACCOUNT_NAME in self.dict_message[USER] \
               and STATUS in self.dict_message[USER]:
            action = PRESENCE
        else:
            action = None
        return action

    def _msg_check(self):
        """
        Проверка на правильный msg формат сообщения
        :return: string, тип действия в сообщении или None если сообщение не правильное
        """
        if self.dict_message.get(ACTION) == MSG \
               and TIME in self.dict_message \
               and TO in self.dict_message \
               and FROM in self.dict_message \
               and ENCODING in self.dict_message \
               and MESSAGE in self.dict_message:
            action = MSG
        else:
            action = None
        return action

    def response_message_create(self, sock, code=OK, with_message=True, message_text='Ok', quantity=0,
                                send_message=True):
        """
        Метод создающий сообщения-ответы в зависимости от кода ответа для клиента и других параметров
        """
        if with_message:
            if code == OK:
                msg = {ALERT: message_text}
            elif code == ACCEPTED:
                msg = {QUANTITY: quantity}
            else:
                msg = {ERROR: message_text}
            self.dict_message = msg
        self.dict_message.update({RESPONSE: code})
        if code != ACCEPTED:
            self.dict_message.update(time=int(time.time()))
        self.encode_message()
        if send_message and isinstance(sock, socket.socket):
            self.send_message(sock)


if __name__ == '__main__':
    message_byte = b'{"action": "presence", "time": 1519377276, "type": "status", "user": ' \
                   b'{"account_name": "MOTHER_OF_DRAGON", "status": "Hello"}}'
    message_dict = {123456: 12335}
    m = Message(message_byte)
    m2 = Message(message_dict)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s = open_client_socket('localhost', 7777)
    m.send_rcv_message(s)
    print(m.dict_message)
    m.rcv_message(s)
    print(m.dict_message)
    print(s.getpeername())
    s.close()
