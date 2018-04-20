import sys
import time
import socket
import select
import logging
import sqlalchemy.exc

from threading import Thread, Lock
from queue import Queue

from system.jim_v2 import JIMMessage, find_cli_key_and_argument
from system.metaclasses import ClientVerifier
from system.errors import WrongPortError
from system.db.client_db_worker import ClientWorker
from system.config import *
from system import hashing

log_client = logging.getLogger('messenger.client')
log_debug = logging.getLogger('messenger.debug')
message_lock = Lock()

que = Queue()


class Client(metaclass=ClientVerifier):
    """
    Класс представлен необходимыми методами и свойствами для работы клиента.
    Метаклассом для этого класса послужил ClientVerifier, выполняющий функцию проверки
    используемых методов в данном классе.
    При инициализации экземпляра класса, передаются значения удалённого хоста и порт сервера,
    с которым будет осуществлять взаимодействия
    """
    def __init__(self, hostname='localhost', port=7777):
        self.def_hostname = hostname
        self.def_port = port
        # read_ и write_ нужны для проверки, если клиент был запущен из консоли только в одном режиме
        self._read = False
        self._write = False
        self.alive = True
        self.hostname, self.port = self._cli_param_get()
        self.username = ''
        self.client_db = None
        self.m = JIMMessage()
        self.m_r = JIMMessage()
        self._cli_param_get()

    def _cli_param_get(self):
        """
        Установить значение порта и адреса исходя из переданных данных, при запуске через командную строку
        :return:
        """
        try:
            port = int(find_cli_key_and_argument('-p', self.def_port))
        except ValueError:
            raise WrongPortError
        addr = find_cli_key_and_argument('-a', self.def_hostname)
        self._read = '-r' in sys.argv
        self._write = '-w' in sys.argv
        return addr, port

    def open_client_socket(self):
        """
        Создаёт экземпляр класса socket для клиентского приложения
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.hostname, self.port))
        except ConnectionRefusedError:
            raise ConnectionRefusedError("Соединение по {}:{} не возможно".format(self.hostname, self.port))
        return sock

    def start_client(self, sock, username, status="I'm here"):
        self.username = username
        # получаем доступ к принадлежащй данном клиенту базе данных
        self.client_db = ClientWorker('sqlite:///system/db/{}_client_db.db?check_same_thread=False'.
                                      format(self.username))
        self.m.create_presence_message(username, status)
        self.m.send_rcv_message(sock)
        self.receive_contact_messages(sock, self.m)

    def receive_contact_messages(self, sock, message):
        message_lock.acquire()
        message.create_get_contact_message()
        print(message.send_rcv_message(sock))
        quantity = message.dict_message[QUANTITY]
        for _ in range(quantity):
            message.rcv_message(sock)
            try:
                self.client_db.add_contact(message.dict_message[USER_ID])
            except sqlalchemy.exc.IntegrityError:
                print('Клиент уже есть')
            print(message.dict_message)
        message_lock.release()

    def get_all_contacts(self):
        self.client_db.session.rollback()
        return self.client_db.get_all_contacts()

    def change_contact_global(self, sock, username='MUSEUN', add=True):
        message_lock.acquire()
        self.m.create_change_contact_message(username, add=add)
        self.m.send_rcv_message(sock)
        print(self.m.dict_message)
        if self.m.dict_message[RESPONSE] == 200:
            ok = True
        else:
            ok = False
        message_lock.release()
        return ok

    def add_contact_local(self, contact='MUSEUN'):
        self.client_db.add_contact(contact)

    def del_contact_local(self, contact='MUSEUN'):
        self.client_db.del_contact(contact)

    def check_local_contact(self, contact=''):
        if contact not in self.client_db.get_all_contacts():
            ok = True
        else:
            ok = False
        return ok

    def send_msg_message(self, sock, to, from_, text):
        message_lock.acquire()
        self.m.create_msg_message(False, to, from_, text)
        self.client_db.add_to_history(to, time.ctime(), text, True)
        self.m.send_rcv_message(sock)
        message_lock.release()

    def load_messages_from_history(self, contact=''):
        return self.client_db.get_messages_from_history(contact)

    def cycle_read_messages(self, sock, queue):
        while self.alive:
            wait = 0.5
            r, w, e = select.select([sock], [sock], [], wait)
            for sock_ in r:
                self.m_r.rcv_message(sock_)
                if self.m_r.dict_message[ACTION] == MSG:
                    self.client_db.session.rollback()
                    self.client_db.add_to_history(self.m_r.dict_message[FROM], time.ctime(),
                                                  self.m_r.dict_message[MESSAGE], False)
                    print(self.m_r.dict_message)
                    queue.put(self.m_r.dict_message)
                    self.m_r.clean_buffer()

    def cli_interact(self, sock):
        while self.alive:
            action = input('>>')
            if action == 'send':
                to_ = input('>>Кому отправить: ')
                text = input('>>Текст сообщения: ')
                self.send_msg_message(sock, to=to_, from_=self.username, text=text)
                pass
            elif action == 'show':
                for i in self.get_all_contacts():
                    print(i)
            elif action == 'add':
                new = input('>>Введите имя контакта: ')
                if self.check_local_contact(new):
                    if self.change_contact_global(sock, new):
                        self.add_contact_local(new)
                        print('Клиент добавлен')
            elif action == 'del':
                del_ = input('>>Введите имя контакта: ')
                if not self.check_local_contact(del_):
                    if self.change_contact_global(sock, del_, False):
                        self.del_contact_local(del_)
                        print('Клиент удален')
            elif action == 'end':
                self.alive = False
                break
            else:
                print('Не верное действие')


if __name__ == '__main__':
    client = Client()
    sock_ = client.open_client_socket()
    usr = input('Имя пользователя: ')
    pswd = input('Пароль: ')
    pswd_hash = hashing.get_safe_hash(pswd)
    print(client.m.create_auth_message(usr, pswd_hash))
    client.m.send_rcv_message(sock_)
    client.start_client(sock_, usr)
    thread = Thread(target=client.cycle_read_messages, args=[sock_, que])
    thread.daemon = False
    thread2 = Thread(target=client.cli_interact, args=[sock_])
    thread2.daemon = False
    thread.start()
    thread2.start()


