# import sys
import select
import socket
import logging
import time

from threading import Thread
from queue import Queue

from system.jim_v2 import JIMResponse, JIMMessage, find_cli_key_and_argument, get_safe_hash
from system.errors import ClosedSocketError, WrongPortError, WrongInterfaceError
from system.db import server_db_worker
from system.metaclasses import ServerVerifier
from system.config import *

log_server = logging.getLogger('messenger.server')
server_db = server_db_worker.ServerWorker('sqlite:///system/db/server_db.db?check_same_thread=False')
input_q = Queue()


class Handler(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print('Инициализация')
        self.queue = input_q
        self.message = None
        self.action = None
        self.sock = None
        self.clients = None
        self.active = True

    def _get_from_queue(self):
        item = self.queue.get()
        print(item)
        self.message = JIMResponse(item['text'])
        self.action = item['action']
        self.sock = item['sock']
        self.clients = item['clients']

    def handling_action(self):
        if self.action == PRESENCE:
            self._presence_handle()
        elif self.action == MSG:
            self._msg_handle()
        elif self.action == GET_CONTACTS:
            self._get_contacts_handle()
        elif self.action == ADD_CONTACT:
            self._add_del_contact_handle()
        elif self.action == DEL_CONTACT:
            self._add_del_contact_handle(False)
        # TODO протестировать работу обоих методов
        elif self.action == JOIN:
            self._join_handle()
        elif self.action == LEAVE:
            self._leave_handle()
        elif self.action == AUTH:
            self._auth_handle()
        elif self.action == REGISTER:
            self._register_handle()
        else:
            self.message.response_message_create(self.sock, WRONG_REQUEST)

    # TODO сделать проще... как можно восстановить сокет из fd?
    def _msg_handle(self):
        if '#' in self.message.dict_message[TO]:
            # print('chat')
            room = self.message.dict_message[TO][1:]
            contacts = server_db.get_room_members(room)
            for contact in contacts:
                if contact != self.message.dict_message[FROM]:
                    sockets = server_db.get_client_sockets(contact)
                    for sock_ in sockets:
                        for sock_online in self.clients:
                            if sock_ == sock_online.fileno():
                                self.message.send_message(sock_online)
        else:
            print(self.message.dict_message)
            sockets = server_db.get_client_sockets(self.message.dict_message[TO])
            for sock_ in sockets:
                for sock_online in self.clients:
                    if sock_ == sock_online.fileno():
                        self.message.send_message(sock_online)
                        print('Сообщение отправлено!')
            self.message.response_message_create(self.sock, OK)

    def _auth_handle(self):
        client_name = self.message.dict_message[USER][ACCOUNT_NAME]
        client = server_db.request_client(client_name)
        if client is None:
            self.message.response_message_create(self.sock, NOT_FOUND, message_text="Пользователь не существует")
        else:
            client_hash = self.message.dict_message[USER][PASSWORD]
            if client.hash[0].hashpass == client_hash:
                print('{} авторизован'.format(client_name))
                self.message.response_message_create(self.sock, OK)
            else:
                print('{} не авторизован'.format(client_name))
                self.message.response_message_create(self.sock, WRONG_COMBINATION, message_text='')

    def _register_handle(self):
        client_name = self.message.dict_message[USER][ACCOUNT_NAME]
        pswd = self.message.dict_message[USER][PASSWORD]
        # проверяем, если клиент с таким именем уже не зарегистрирован в нашем мессенджере
        client = server_db.request_client(client_name)
        if client is None:
            server_db.add_client(client_name, "Yep, i'm here")
            hash_ = get_safe_hash(pswd, SALT)
            print(hash_)
            server_db.register_new_hash(client_login=client_name, hash_=hash_)
            self.message.response_message_create(self.sock, OK)
        else:
            self.message.response_message_create(self.sock, code=CONFLICT, with_message=True,
                                                 message_text="Account is in use", send_message=True)

    def _leave_handle(self):
        room_name = self.message.dict_message[ROOM]
        client = server_db.ident_client_by_sockets(self.sock.fileno())
        room = server_db.request_room(room_name)
        if room and client:
            server_db.join_leave_room(room_name, client)
            self.message.response_message_create(self.sock, 200, True, 'Вы покинули чат')
        else:
            # print('Данной комнаты не существует')
            self.message.response_message_create(self.sock, 400, True, 'Данной комнаты не существует')

    def _join_handle(self):
        room_name = self.message.dict_message[ROOM]
        client = server_db.ident_client_by_sockets(self.sock.fileno())
        room = None
        while not room:
            room = server_db.request_room(room_name)
            if room:
                server_db.join_leave_room(room_name, client)
                self.message.response_message_create(self.sock, 200, True, 'Вы успешно присоединились к чату')
            else:
                server_db.add_room(room_name)

    def _presence_handle(self):
        username = self.message.dict_message[USER][ACCOUNT_NAME]
        client = server_db.request_client(username)
        if client is None:
            self.message.response_message_create(self.sock, NOT_FOUND, message_text='Пользователь не найден')
        else:
            server_db.add_to_history(username,
                                     self.message.dict_message[TIME],
                                     self.sock.getpeername()[0])
            server_db.add_online_client(username, self.sock.fileno())
            self.message.response_message_create(self.sock, OK)
        # while not client:
        #     client = server_db.request_client(username)
        #     if client:
        #         server_db.add_to_history(username,
        #                                  self.message.dict_message[TIME],
        #                                  self.sock.getpeername()[0])
        #         print("Клиент уже есть")
            # else:
            #     server_db.add_client(username,
            #                          self.message.dict_message[USER][STATUS])
            #     print("Клиент добавлен")
        # server_db.add_online_client(username, self.sock.fileno())
        # self.message.response_message_create(self.sock, OK)

    def _get_contacts_handle(self):
        client = server_db.ident_client_by_sockets(self.sock.fileno())
        # print (client)
        contacts_quantity = server_db.count_contacts(client)
        contacts = server_db.get_all_contacts(client)
        self.message.response_message_create(sock=self.sock, code=ACCEPTED,
                                             quantity=contacts_quantity)
        contact_info_message = JIMMessage()
        for contact in contacts:
            contact_info_message.create_server_contact_list(contact.login)
            contact_info_message.send_message(self.sock)
            time.sleep(0.3)

    def _add_del_contact_handle(self, add=True):
        client = server_db.ident_client_by_sockets(self.sock.fileno())
        if client:
            print(client)
            if self.message.dict_message[USER_ID] not in server_db.get_all_contacts(client):
                if add:
                    server_db.add_contacts(client, self.message.dict_message[USER_ID])
                else:
                    server_db.del_contact(client, self.message.dict_message[USER_ID])
                self.message.response_message_create(sock=self.sock, code=OK, with_message=False)
            else:
                self.message.response_message_create(sock=self.sock, code=400, with_message=False)
        else:
            print('Клиента с таким сокетом не существует')
            self.message.response_message_create(WRONG_REQUEST, with_message=False)

    def run(self):
        print("i'm running")
        while True:
            if not self.queue.empty():
                self._get_from_queue()
                self.handling_action()
            if not self.active:
                break
        return


class Server(metaclass=ServerVerifier):
    def __init__(self, default_if_add='', default_port=7777, connections=5, sock_timeout=None):
        self._def_if_add = default_if_add
        self._def_port = default_port
        self.connections = connections
        self.sock_timeout = sock_timeout
        self.if_add, self.port = self._cli_param_get()

    def _cli_param_get(self):
        """
        Функция возвращаюшая параметры адреса и порта, заданные через командную строку,
        иначе, возвращаются дефолтные значения переданные методу find_cli_key_and_argument
        :return: кортеж, host и порт, заданные через командную строку
        """
        try:
            port = int(find_cli_key_and_argument('-p', self._def_port))
        except ValueError:
            raise WrongPortError
        host = find_cli_key_and_argument('-a', self._def_if_add)
        return host, port

    def _open_server_socket(self):
        """
        Создаёт экземпляр класса socket для серверного приложения, привязывается к заданному порту и начинает слушать
        на наличие соединений.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((self.if_add, self.port))
        except socket.gaierror:
            raise WrongInterfaceError(self.if_add)
        sock.settimeout(self.sock_timeout)
        sock.listen(self.connections)
        return sock

    @staticmethod
    def _remove_bad_client_sock(sock, clients):
        server_db.del_sock(sock.fileno())
        clients.remove(sock)

    def read_sock_streams(self, sock_to_read, clients, timeout=0.5):
        """
        Метод для чтения из сокета приходящие сообщения от клиента
        :param sock_to_read: список сокетов, ожидающие в очереди на чтение
        :param timeout: таймоут для клиентского сокета
        :param clients: список всех сокетов
        """
        for sock in sock_to_read:
            sock.settimeout(timeout)
            m = JIMResponse()
            try:
                m.rcv_message(sock)
                action = m.get_message_action()
                print(action)
                input_q.put({'action': action, 'sock': sock, 'clients': clients, 'text': m.dict_message})

            except (ClosedSocketError, ConnectionResetError, ConnectionAbortedError):
                # если выходит ошибка, значит клиент вышел, не разорвав соединение, удаляем сокет из списка клиентов
                self._remove_bad_client_sock(sock, clients)

    def run_server(self):
        """
        Запускает вечный цикл, обрабатывает подключившихся клиентов и распределяет по очередям:
            на запись
            на чтение
            с ошибкой
        Каждая из очередей, или по другому список сокетов, стоящих в очереди, передаются
        соответсвующим функциям.
        """
        clients = []
        with self._open_server_socket() as s:
            while True:
                try:
                    # обрабатываем соединение
                    client, addr = s.accept()
                except OSError:
                    pass
                else:
                    # добавляем сокет к списку сокетов от других клиентов
                    clients.append(client)
                finally:
                    wait = 0
                    r = []
                    # w = []
                    try:
                        # опрашиваем каждый соект, и проверяем, кто из клиентов какие действия хочет выполнять
                        r, w, e = select.select(clients, clients, [], wait)
                    except OSError:
                        pass
                    self.read_sock_streams(r, clients)
                    # Здесь будет функция, которая будет рассылать probe сообщения всем подключённым клиента
                    # self.write_sock_streams(w, clients)


if __name__ == '__main__':
    serv = Server(sock_timeout=0.5)
    h = Handler()
    h.daemon = True
    h.start()
    serv.run_server()


