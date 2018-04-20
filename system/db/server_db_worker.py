from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
Base = declarative_base()
# Классы и связи для работы с серверной базой данных
ContactList = Table('contact_lists', Base.metadata,
                    Column('owner_id', Integer, ForeignKey('client.id'), primary_key=True),
                    Column('contact_id', Integer, ForeignKey('client.id'), primary_key=True)
                    )

ChatLists = Table('chat_lists', Base.metadata,
                  Column('room_id', Integer, ForeignKey('chat_rooms.id'), primary_key=True),
                  Column('client_id', Integer, ForeignKey('client.id'), primary_key=True)
                  )


class Client(Base):
    """
    Класс представляющий таблицу client в базе данных сервера
    """
    __tablename__ = 'client'
    id = Column(Integer, primary_key=True, unique=True)
    login = Column(String,  unique=True)
    info = Column(String)
    sockets = relationship('ClientOnline', back_populates="client")
    # для доступа к данным из таблицы client_history в серверной базе данных
    client_history = relationship("ClientHistory", back_populates="client")
    # для доступа к данным (список контактов выбранного клиента) из таблицы contact_lists в серверной базе данных
    contact_list = relationship("Client", secondary=ContactList,
                                primaryjoin=id == ContactList.c.owner_id,
                                secondaryjoin=id == ContactList.c.contact_id
                                )
    # список тех, кто имеет данного клиента как один из контактов
    owners_list = relationship("Client", secondary=ContactList,
                               primaryjoin=id == ContactList.c.contact_id,
                               secondaryjoin=id == ContactList.c.owner_id
                               )
    hash = relationship("HashTable", back_populates='client')

    def __init__(self, login, info):
        self.login = login
        self.info = info

    def __repr__(self):
        return "<Client ({}, {}) >".format(self.login, self.info)


class ClientHistory(Base):
    """
    Класс для доступа к таблице client_history в серверной базе данных
    """
    __tablename__ = 'client_history'
    client_id = Column(Integer, ForeignKey('client.id'), primary_key=True)
    login_time = Column(Integer, primary_key=True)
    ip_add = Column(String)
    # Переменная для запроса клиент(а)/ов, который сделал данн(ую)/ые запис(ь)/и в таблице
    client = relationship('Client', back_populates="client_history")

    def __init__(self, client, login_time, ip_add):
        self.client = client
        self.login_time = login_time
        self.ip_add = ip_add

    def __repr__(self):
        return "<client_history ({}, {}, {})>".format(self.client_id, self.login_time, self.ip_add)


class ClientOnline(Base):
    """База данных для сокетов и клиентов"""
    __tablename__ = 'client_online'
    client_id = Column(Integer, ForeignKey('client.id'), primary_key=True)
    sock = Column(Integer, primary_key=True, unique=True)
    client = relationship('Client', back_populates="sockets")

    def __init__(self, client, sock):
        self.client = client
        self.sock = sock

    def __repr__(self):
        return "<ClientOnline ({} {})>".format(self.client_id, self.sock)


class ChatRooms(Base):
    """Таблица комнат для чата"""
    __tablename__ = 'chat_rooms'
    id = Column(Integer, primary_key=True, unique=True)
    room_title = Column(String, unique=True)
    room_members = relationship('Client', secondary=ChatLists)

    def __init__(self, room_title):
        self.room_title = room_title

    def __repr__(self):
        return "<ChatRoom ({}) >".format(self.room_title)


class HashTable(Base):
    """Таблица для храненеия хешей паролей"""
    __tablename__ = 'hash_table'
    user_id = Column(Integer, ForeignKey('client.id'), unique=True, primary_key=True)
    hashpass = Column(Integer, primary_key=True)
    client = relationship('Client', back_populates="hash")

    def __init__(self, client, hashpass):
        self.hashpass = hashpass
        self.client = client

    def __repr__(self):
        return '<Hash ({})>'.format(self.hashpass)


class DbWorker:
    """
    Родительский класс для наследования коассов для работы с серверной или клиентской базы данных
    """
    def __init__(self, db):
        self.engine = create_engine(db)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self._start_session()
        Base.metadata.create_all(self.engine)

    def _start_session(self):
        return self.Session()

    def commit_session(self):
        self.session.commit()


# TODO добавить описание
# TODO добавить логирование через @log
class ServerWorker(DbWorker):
    """
    Класс для работы с серверной базой данных
    """
    def __init__(self, db):
        DbWorker.__init__(self, db)
        # self.drop_all_online_clients()

    def request_client(self, client_login=""):
        try:
            client = self.session.query(Client).filter(Client.login == client_login).one()
        except NoResultFound:
            client = None
        return client

    def add_contacts(self, owner_login, contact_login):
        owner = self.request_client(owner_login)
        contact = self.request_client(contact_login)
        owner.contact_list.append(contact)
        self.commit_session()

    def del_contact(self, owner_login, contact_login):
        try:
            owner = self.request_client(owner_login)
            contact = self.request_client(contact_login)
            owner.contact_list.remove(contact)
            self.commit_session()
        except ValueError:
            print('Контакт уже удалён')

    def add_client(self, login, info):
        new_client = Client(login, info)
        self.session.add(new_client)
        self.commit_session()

    def add_to_history(self, client_login, login_time, ip_add):
        new_history = ClientHistory(self.request_client(client_login), login_time, ip_add)
        self.session.add(new_history)
        self.commit_session()

    def count_contacts(self, client_login):
        client = self.request_client(client_login)
        if client:
            total = len(client.contact_list)
        else:
            total = None
        return total

    def get_all_contacts(self, client_login):
        client = self.request_client(client_login)
        return client.contact_list

    def get_client_sockets(self, client_login):
        client = self.request_client(client_login)
        socket_list = [sock_.sock for sock_ in client.sockets]
        return socket_list

    def add_online_client(self, client_login, sock):
        new_client_online = ClientOnline(self.request_client(client_login), sock)
        self.session.add(new_client_online)
        self.commit_session()

    def ident_client_by_sockets(self, sock):
        try:
            client_online = self.session.query(ClientOnline).filter(ClientOnline.sock == sock).one()
            client_login = client_online.client.login
        except NoResultFound:
            client_login = None
        return client_login

    def del_sock(self, sock):
        try:
            client_online = self.session.query(ClientOnline).filter(ClientOnline.sock == sock).one()
            self.session.delete(client_online)
            self.session.commit()
            print('Сокет {} удалён'.format(sock))
        except NoResultFound:
            print('Сокет {} уже удалён'.format(sock))

    def send_client_offline(self, client_login):
        client = self.request_client(client_login)
        for sock in client.sockets:
            self.session.delete(sock)
        self.commit_session()

    def drop_all_online_clients(self):
        self.session.query(ClientOnline).delete()
        self.commit_session()

    def request_room(self, room_title):
        try:
            room = self.session.query(ChatRooms).filter(ChatRooms.room_title == room_title).one()
        except NoResultFound:
            room = None
        return room

    def get_client_hash(self, client_login):
        client = self.request_client(client_login)
        if client:
            return client.hash[0]
        else:
            return None

    def register_new_hash(self, client_login, hash_):
        client = self.request_client(client_login)
        new_client_hash = HashTable(client, hash_)
        self.session.add(new_client_hash)
        self.commit_session()

    def update_client_hash(self, client_login, hash_):
        client = self.request_client(client_login)
        edited_hash = self.session.query(HashTable).filter(HashTable.user_id == client.id).one()
        edited_hash.hashpass = hash_
        self.commit_session()

    def get_room_members(self, room_title):
        room = self.request_room(room_title)
        return [client.login for client in room.room_members]

    def join_leave_room(self, room_title, client_login, join=True):
        try:
            room = self.request_room(room_title)
            client = self.request_client(client_login)
            if join:
                room.room_members.append(client)
            else:
                room.room_members.remove(client)
            self.commit_session()
        except ValueError:
            print('Клиент уже покинул комнату')

    def add_room(self, room_title):
        new_room = ChatRooms(room_title)
        self.session.add(new_room)
        self.commit_session()


if __name__ == '__main__':
    test = ServerWorker('sqlite:///server_db.db')
    # test.add_client('son', 'nothing')
    print(test.get_client_hash('test').hashpass)
    # test.get_client_hash('test')
    test.update_client_hash('test', 99999)
    test.register_new_hash('MUSEUN', 123456789111)
    print(test.get_client_hash('MUSEUN'))
    test.update_client_hash('MUSEUN', 11111)
    print(test.get_client_hash('MUSEUN'))