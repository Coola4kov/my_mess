from bson.objectid import ObjectId
from mongoengine import EmbeddedDocument, Document, BooleanField, \
    StringField, BinaryField, EmbeddedDocumentField, \
    ListField, ReferenceField, ObjectIdField, IntField, connect

import subprocess
import time
import os


class Visit(EmbeddedDocument):
    login_time = StringField(required=True)
    ip_add = StringField(required=True)


class Client(Document):
    login = StringField(required=True, unique=True)
    info = StringField(default="I'm here")
    image = StringField()
    history = ListField(EmbeddedDocumentField(Visit))
    contacts = ListField(ReferenceField('self', unique=True))
    owners = ListField(ReferenceField('self', unique=True))
    hash = StringField(required=True)


class Room(Document):
    name = StringField(required=True, unique=True)
    members = ListField(ReferenceField(Client))


class Sockets(Document):
    client = ReferenceField(Client, required=True)
    fd = IntField(unique=True, required=True)


class ServerDb:
    def __init__(self, name='server_db'):
        # path_server = os.path.join(os.getcwd(), 'MongoDB', 'Server', '3.6', 'bin', 'mongod.exe')
        # path_db = os.path.join(os.getcwd(), 'mng_db')
        # subprocess.Popen([path_server, '--dbpath', path_db])
        connect(name)

    # Clients
    def request_client(self, login):
        if self.check_client(login):
            client = Client.objects(login=login)
        else:
            client = None
        return client

    @staticmethod
    def check_client(login):
        if Client.objects(login=login):
            here = True
        else:
            here = False
        return here

    def add_client(self, login='', hash_='', info="I'm here"):
        if not self.check_client(login):
            Client(login=login, hash=hash_, info=info).save()
            added = True
        else:
            added = False
        return added

    def get_client_id(self, login, check=True):
        if not check:
            id_ = self.request_client(login).get().id
        else:
            if self.check_client(login):
                id_ = self.request_client(login).get().id
            else:
                id_ = None
        return id_

    # Hash
    def get_hash(self, login):
        if self.check_client(login):
            hash_ = self.request_client(login).get().hash
        else:
            hash_ = None
        return hash_

    # Room
    @staticmethod
    def get_room_members(room=''):
        room = Room.objects(room=room)
        if room:
            room_members = [client.login for client in room.get().members]
        else:
            room_members = []
        return room_members

    # Contacts
    def edit_contacts(self, owner_login, contact_login, add=True):
        if self.check_client(owner_login) and self.check_client(contact_login):
            owner = self.request_client(owner_login)
            contact = self.request_client(contact_login)
            if add:
                owner.update_one(add_to_set__contacts=contact.get().id)
                contact.update_one(add_to_set__owners=owner.get().id)
            else:
                contact_id = contact.get().id
                print(owner.update_one(pull__contacts=contact_id))
                print(contact.update_one(pull__owners=owner.get().id))
            added = True
        else:
            added = False
        return added

    def count_contacts(self, owner_login):
        if self.check_client(owner_login):
            owner = self.request_client(owner_login)
            total_contacts = len(owner.get().contacts)
        else:
            total_contacts = None
        return total_contacts

    def get_all_contacts(self, owner_login):
        if self.check_client(owner_login):
            owner = self.request_client(owner_login)
            contacts = [contact.login for contact in owner.get().contacts]
        else:
            contacts = []
        return contacts

    def search_contact_ilike(self, login_='',contact_ilike=''):
        owner_id = Client.objects.get(login=login_).id
        contacts_ = Client.objects.filter(owners=owner_id, login__icontains=contact_ilike)
        return [contact.login for contact in contacts_]
        #  clients_ = Client.objects.filter(login__icontains=contact_ilike)
        # contacts_ = Client.objects(login=login_).filter()

    # History
    def add_to_history(self, login, login_time, ip_add):
        if self.check_client(login):
            client = self.request_client(login)
            history_line = Visit(str(login_time), ip_add)
            client.update_one(push__history=history_line)
            added = True
        else:
            added = False
        return added

    # Image
    def add_img(self, login='', img_base64=''):
        if self.check_client(login):
            client = self.request_client(login)
            client.update_one(image=img_base64)
            added = True
        else:
            added = False
        return added

    def get_img(self, login=''):
        if self.check_client(login):
            client = self.request_client(login)
            img = client.get(login=login).image
        else:
            img = ''
        return img

    # Sockets
    def get_socket_by_client(self, login=''):
        socket_ = Sockets.objects(client=self.get_client_id(login, False))
        if self.check_client(login) and socket_:
            fd = socket_.get().fd
        else:
            fd = None
        return fd

    @staticmethod
    def get_client_by_socket(fd=0):
        socket_ = Sockets.objects(fd=fd)
        if socket_:
            client_id = socket_.get().client.login
        else:
            client_id = None
        return client_id

    def add_socket(self, login='', fd=0):
        if self.check_client(login):
            id_ = Sockets(client=self.get_client_id(login, False), fd=fd).save()
        else:
            id_ = None
        return id_

    def drop_socket(self, login='', fd=0):
        if login:
            if self.check_client(login):
                deleted = Sockets.objects(client=self.get_client_id(login, False)).delete()
            else:
                deleted = False
        elif fd:
            socket_ = Sockets.objects(fd=fd)
            if socket_:
                deleted = socket_.delete()
            else:
                deleted = False
        else:
            deleted = False
        return deleted

    @staticmethod
    def drop_sockets():
        Sockets.drop_collection()



if __name__ == '__main__':
    server = ServerDb()
    # Client.drop_collection()
    # Client(login='test', hash='123456789').save()
    # Client(login='test2', hash='1234567859').save()
    # Client(login='test3', hash='1234').save()
    # server.edit_contact('test', 'test3')
    # server.edit_contact('test', 'test3')
    # server.edit_contact('test', 'test2')
    # server.edit_contact('test', 'test2')
    # server.add_client('lol', '123456')
    # server.edit_contact('test', 'lol')
    # print(server.count_contact('test'))
    # print(server.get_all_contacts('test'))
    # server.add_to_history('test', time.ctime(), '192.168.6.15')
    # server.add_img('test', '987654321')
    # print(server.get_img('test'))
    # Sockets(client=server.request_client('test').get().id, fd=987).save()
    # print(server.get_socket_by_client('test'))
    # print(server.get_client_by_socket(123))
    print(server.get_hash('MAMA'))
    # print(server.add_socket('MAMA', 1234))
    # print(server.drop_socket('MAMA'))
    # server.edit_contacts('test', 'MAMA', False)
    print(server.search_contact_ilike('test', 'A'))
