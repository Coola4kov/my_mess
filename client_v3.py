import sys
import time
import socket
import select
import logging
import sqlalchemy.exc

from threading import Thread, Lock
from queue import Queue

from system.jim_v2 import JIMMessage, find_cli_key_and_argument, get_safe_hash
from system.metaclasses import ClientVerifier
from system.errors import WrongPortError
from system.db.client_db_worker import ClientWorker
from system.config import *

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
        self.sock = self.open_client_socket()

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

    @staticmethod
    def user_credentials_req():
        usr = input('Имя пользователя: ')
        pswd = input('Пароль: ')
        return usr, pswd

    def authorization(self, usr='', pswd=''):
        pswd_hash = get_safe_hash(pswd, SALT)
        self.m.create_auth_reg_message(usr, pswd_hash)
        self.m.send_rcv_message(self.sock)
        resp = self.m.dict_message[RESPONSE]
        # print(resp)
        if resp == OK:
            print("{} авторизован, приятного пользования".format(usr))
            auth_confirm = True
            # return "{} авторизован, приятного пользования".format(usr)
        elif resp == WRONG_COMBINATION:
            print("Не верный логин или пароль")
            auth_confirm = False
            # return "Не верный логин или пароль"
        else:
            print("Пользователя не существует")
            auth_confirm = False
        if not auth_confirm:
            print('Попробуйте ещё раз')
        return auth_confirm

    def registration(self, usr='', pswd=''):
        self.m.create_auth_reg_message(usr, pswd, registration=True)
        self.m.send_rcv_message(self.sock)
        resp = self.m.dict_message[RESPONSE]
        if resp == OK:
            print('Вы зарегистрировались, приятного пользования')
            reg = True
        elif resp == CONFLICT:
            print('Пользователь с такими именем уже существует')
            reg = False
        else:
            print('Регистрация не удалась')
            reg = False
        if not reg:
            print('Попробуйте ещё раз')
        return reg

    def start_client(self, usr="", pswd="", status="I'm here"):
        if not usr:
            reg = False
            while not reg:
                ans = input('Вы зарегистрированны? y/n: ')
                ans = ans.upper()
                if ans == 'N':
                    usr, pswd = self.user_credentials_req()
                    reg = self.registration(usr, pswd)
                elif ans == 'Y':
                    reg = True
            auth = False
            while not auth:
                usr, pswd = self.user_credentials_req()
                auth = self.authorization(usr, pswd)
        self.username = usr
        # получаем доступ к принадлежащй данному клиенту базе данных
        self.client_db = ClientWorker('sqlite:///system/db/{}_client_db.db?check_same_thread=False'.
                                      format(self.username))
        self.m.create_presence_message(usr, status)
        self.m.send_rcv_message(self.sock)
        self.receive_contact_messages()

    def receive_contact_messages(self):
        message_lock.acquire()
        self.m.create_get_contact_message()
        print(self.m.send_rcv_message(self.sock))
        quantity = self.m.dict_message[QUANTITY]
        for _ in range(quantity):
            self.m.rcv_message(self.sock)
            try:
                self.client_db.add_contact(self.m.dict_message[USER_ID])
            except sqlalchemy.exc.IntegrityError:
                print('Клиент уже есть')
            print(self.m.dict_message)
        message_lock.release()

    def get_all_contacts(self):
        self.client_db.session.rollback()
        return self.client_db.get_all_contacts()

    def change_contact_global(self, username='MUSEUN', add=True):
        message_lock.acquire()
        self.m.create_change_contact_message(username, add=add)
        self.m.send_rcv_message(self.sock)
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
        if contact in self.client_db.get_all_contacts():
            ok = True
        else:
            ok = False
        return ok

    def send_msg_message(self, to, from_, text):
        message_lock.acquire()
        self.m.create_msg_message(False, to, from_, text)
        self.client_db.add_to_history(to, time.ctime(), text, True)
        self.m.send_rcv_message(self.sock)
        message_lock.release()

    def load_messages_from_history(self, contact=''):
        return self.client_db.get_messages_from_history(contact)

    def cycle_read_messages(self, queue):
        while self.alive:
            wait = 0.5
            r, w, e = select.select([self.sock], [self.sock], [], wait)
            for sock_ in r:
                self.m_r.rcv_message(sock_)
                if self.m_r.dict_message[ACTION] == MSG:
                    self.client_db.session.rollback()
                    self.client_db.add_to_history(self.m_r.dict_message[FROM], time.ctime(),
                                                  self.m_r.dict_message[MESSAGE], False)
                    print(self.m_r.dict_message)
                    queue.put(self.m_r.dict_message)
                    self.m_r.clean_buffer()

    def cli_interact(self):
        while self.alive:
            action = input('>>')
            if action == 'send':
                to_ = input('>>Кому отправить: ')
                text = input('>>Текст сообщения: ')
                self.send_msg_message(to=to_, from_=self.username, text=text)
                pass
            elif action == 'show':
                for i in self.get_all_contacts():
                    print(i)
            elif action == 'add':
                new = input('>>Введите имя контакта: ')
                if self.check_local_contact(new):
                    if self.change_contact_global(new):
                        self.add_contact_local(new)
                        print('Клиент добавлен')
                    else:
                        print('Не удаётся добавить клиента')
            elif action == 'del':
                del_ = input('>>Введите имя контакта: ')
                if not self.check_local_contact(del_):
                    if self.change_contact_global(del_, False):
                        self.del_contact_local(del_)
                        print('Клиент удален')
                else:
                    print('Не удаётся удалить клиента')
            elif action == 'img':
                self.img_announce()
            elif action == 'img_send':
                id_ = input('>>Введите ID изображения')
                self.img_send(id_)
            elif action == 'end':
                self.alive = False
                break
            else:
                print('Не верное действие')

    def img_announce(self):
        self.m.create_img_message(100)
        self.m.send_message(self.sock)
        print(self.m.dict_message[IMG_ID])

    def img_send(self, img_id, part='', seq=1):
        self.m.create_img_parts_message(data='HELLO', seq=seq, id_=img_id)
        self.m.send_message(self.sock)


if __name__ == '__main__':
    client = Client()
    # sock_ = client.open_client_socket()
    client.start_client()
    thread = Thread(target=client.cycle_read_messages, args=[que])
    thread.daemon = False
    thread2 = Thread(target=client.cli_interact)
    thread2.daemon = False
    thread.start()
    thread2.start()


