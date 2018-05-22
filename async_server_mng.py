import asyncio
import functools
import subprocess
import time

from system.jim_v2 import JIMResponse, JIMMessage, get_safe_hash
from system.image_worker import ImageWorker
from system.db.serv_mongo_db import ServerDb
from system.config import *


class ServerProtocol(asyncio.Protocol):
    def __init__(self, db, img_parts, clients):
        self.server_db = db
        self.img_parts = img_parts
        self.clients = clients
        self.timer = 0
        self.stop_timer = False
        # self.loop_timer = asyncio.get_event_loop()
        self.action = None
        self.message = None
        self.socket = None
        self.fd = None
        self.transport = None

    def connection_made(self, transport):
        self.socket = transport.get_extra_info('socket')
        self.fd = self.socket.fileno()
        self.timer = asyncio.get_event_loop().time()
        self.transport = transport
        # self.loop_timer.run_until_complete(self.timer_check())
        asyncio.ensure_future(self.timer_check())

    def data_received(self, data):
        print(data)
        try:
            self.message = JIMResponse(data)
        except:
            # не получается отловить exception в другом, не асинхронном модуле jim_v2.py.
            self.message = JIMResponse()
            self.message.encoded_message = data
            self.message.decode_to_few_messages()
        if self.message.list_of_dicts:
            for i in self.message.list_of_dicts:
                self.message.dict_message = i
                self.pass_to_handler()
        else:
            self.pass_to_handler()

    def pass_to_handler(self):
        self.action = self.message.dict_message[ACTION]
        print(self.message)
        self.handle_request()

    def connection_lost(self, exc):
        print('Соединение закрыто')
        # self.loop_timer.stop()
        if not self.stop_timer:
            self.clients.remove(self.socket)
        self.server_db.drop_socket(fd=self.fd)

    async def timer_check(self):
        while not self.stop_timer:
            # print('time_check')
            # print(self.clients)
            await asyncio.sleep(10)
            current_time = asyncio.get_event_loop().time()
            if current_time - self.timer > 30:
                self.clients.remove(self.socket)
                self.stop_timer = True
                self.transport.close()

    def handle_request(self):
        if self.action == AUTH:
            self._auth_handle()
        elif self.action == MSG:
            self._msg_handle()
        elif self.action == PRESENCE:
            self._presence_handle()
        elif self.action == GET_CONTACTS:
            self._get_contacts_handle()
        elif self.action == GET_CONTACT_IMG:
            print('Запрос изображений')
            self._get_contact_img_handle()
        elif self.action == ADD_CONTACT:
            self._add_del_contact_handle()
        elif self.action == DEL_CONTACT:
            self._add_del_contact_handle(False)
        elif self.action == JOIN:
            self._join_handle()
        elif self.action == LEAVE:
            self._leave_handle()
        elif self.action == REGISTER:
            self._register_handle()
        elif self.action == IMG or self.action == IMG_PARTS:
            img_worker = ImageWorker(self.socket, self.message, self.img_parts)
            img_worker.handle(self.action)
            self._whole_message_check(img_worker)
        else:
            self.message.response_message_create(code=WRONG_REQUEST, send_message=False)
            self.transport.write(self.message.encoded_message)

    def _auth_handle(self):
        client_name = self.message.dict_message[USER][ACCOUNT_NAME]
        client = self.server_db.request_client(client_name)
        if client is None:
            self.message.response_message_create(code=NOT_FOUND, message_text="Пользователь не существует",
                                                 send_message=False)
        else:
            client_hash = self.message.dict_message[USER][PASSWORD]
            if client.get().hash == client_hash:
                print('{} авторизован'.format(client_name))
                self.server_db.add_socket(client_name, self.socket.fileno())
                self.clients.append(self.socket)
                self.message.response_message_create(code=OK, send_message=False)
            else:
                print('{} не авторизован'.format(client_name))
                self.message.response_message_create(code=WRONG_COMBINATION, send_message=False)
        self.transport.write(self.message.encoded_message)

    def _msg_handle(self):
        if '#' in self.message.dict_message[TO]:
            # print('chat')
            room = self.message.dict_message[TO][1:]
            contacts = self.server_db.get_room_members(room)
            for contact in contacts:
                if contact != self.message.dict_message[FROM]:
                    sockets = self.server_db.get_client_by_socket(contact)
                    for sock_fn in sockets:
                        for sock_online in self.clients:
                            if sock_fn == sock_online.fileno():
                                self.message.send_message(sock_online)
        else:
            sock_fn = self.server_db.get_socket_by_client(self.message.dict_message[TO])
            # for sock_fn in sockets:
            for sock_online in self.clients:
                if sock_fn == sock_online.fileno():
                    self.message.send_message(sock_online)
                    # self.transport.sendto(self.message.encoded_message, sock_online)
                    print('Сообщение отправлено!')
        self.message.response_message_create(OK, send_message=False)
        self.transport.write(self.message.encoded_message)

    def _presence_handle(self):
        self.timer = asyncio.get_event_loop().time()
        username = self.message.dict_message[USER][ACCOUNT_NAME]
        client = self.server_db.request_client(username)
        if client is None:
            self.message.response_message_create(code=NOT_FOUND, message_text='Пользователь не найден',
                                                 send_message=False)
        else:
            self.server_db.add_to_history(username,
                                          time.time(),
                                          self.socket.getpeername()[0])
            self.message.response_message_create(self.socket, OK, send_message=False)
        self.transport.write(self.message.encoded_message)

    def _get_contacts_handle(self):
        client = self.server_db.get_client_by_socket(self.socket.fileno())
        contacts_quantity = self.server_db.count_contacts(client)
        contacts = self.server_db.get_all_contacts(client)
        self.message.response_message_create(code=ACCEPTED,
                                             quantity=contacts_quantity,
                                             send_message=False)
        self.transport.write(self.message.encoded_message)
        contact_info_message = JIMMessage()
        for contact in contacts:
            contact_info_message.create_server_contact_list(contact)
            self.transport.write(contact_info_message.encoded_message)

    def _get_contact_img_handle(self):
        contact_name = self.message.dict_message[USER_ID]
        client = self.server_db.request_client(contact_name)
        if client:
            img = self.server_db.get_img(contact_name)
            if img:
                img_message = JIMMessage()
                img_sender = ImageWorker(self.socket, img_message, self.img_parts)
                img_sender.img_send(img, contact_name)

    def _add_del_contact_handle(self, add=True):
        new_user = self.message.dict_message[USER_ID]
        if self.server_db.request_client(new_user) is None:
            self.message.response_message_create(NOT_FOUND, with_message=False, send_message=False)
        else:
            client = self.server_db.get_client_by_socket(self.socket.fileno())
            if client:
                contacts = self.server_db.get_all_contacts(client)
                if (add and new_user not in contacts)\
                        or (not add and new_user in contacts):
                    self.server_db.edit_contacts(client, new_user, add)
                    self.message.response_message_create(OK, with_message=False, send_message=False)
                else:
                    self.message.response_message_create(WRONG_REQUEST, with_message=False, send_message=False)
            else:
                print('Клиента с таким сокетом не существует')
                self.message.response_message_create(WRONG_REQUEST,
                                                     message_text='Сокет не зарегистрирован', send_message=False)
        self.transport.write(self.message.encoded_message)

    def _register_handle(self):
        client_name = self.message.dict_message[USER][ACCOUNT_NAME]
        pswd = self.message.dict_message[USER][PASSWORD]
        # проверяем, если клиент с таким именем уже не зарегистрирован в нашем мессенджере
        # client = self.server_db.request_client(client_name)
        client = self.server_db.request_client(client_name)
        if client is None:
            hash_ = get_safe_hash(pswd, SALT)
            self.server_db.add_client(client_name, hash_, "Yep, i'm here")
            self.message.response_message_create(OK, send_message=False)
        else:
            self.message.response_message_create(code=CONFLICT, with_message=True,
                                                 message_text="Account is in use", send_message=False)
        self.transport.write(self.message.encoded_message)

    def _leave_handle(self):
        room_name = self.message.dict_message[ROOM]
        client = self.server_db.ident_client_by_sockets(self.socket.fileno())
        room = self.server_db.request_room(room_name)
        if room and client:
            self.server_db.join_leave_room(room_name, client)
            self.message.response_message_create(OK, True,
                                                 'Вы покинули чат', send_message=False)
        else:
            self.message.response_message_create(WRONG_REQUEST, True,
                                                 'Данной комнаты не существует', send_message=False)
        self.transport.write(self.message.encoded_message)

    def _join_handle(self):
        room_name = self.message.dict_message[ROOM]
        client = self.server_db.ident_client_by_sockets(self.socket.fileno())
        room = None
        while not room:
            room = self.server_db.request_room(room_name)
            if room:
                self.server_db.join_leave_room(room_name, client)
                self.message.response_message_create(OK, True, 'Вы успешно присоединились к чату', send_message=False)
            else:
                self.server_db.add_room(room_name)
        self.transport.write(self.message.encoded_message)

    def _whole_message_check(self, img_worker):
        if img_worker.whole_received_img:
            self.server_db.add_img(img_worker.whole_received_img[USER_ID],
                                   img_worker.whole_received_img[IMG])


async def probe_message_send(clients_):
    m = JIMMessage()
    while True:
        cli_copy = clients_[:]
        await asyncio.sleep(5)
        m.create_probe_message()
        for sock_ in cli_copy:
            try:
                m.send_message(sock_)
                print('probe sent')
            except OSError:
                pass

def server_run():
    server_db = ServerDb()
    server_db.drop_sockets()
    img_parts = {}
    clients = []

    loop = asyncio.get_event_loop()
    coro = loop.create_server(functools.partial(ServerProtocol, server_db, img_parts, clients),
                              '127.0.0.1', 7777)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))

    probe_loop = asyncio.get_event_loop()
    probe_loop.run_until_complete(probe_message_send(clients))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        probe_loop.stop()

    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


if __name__ == '__main__':
    server_run()

