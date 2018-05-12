import pymongo
import mongoengine
import time
import os
import subprocess

# client = pymongo.MongoClient()
#
# db = client.test_database
# contacts = db.contacts
#
# contact = {"name": "test",
#            "img_base64": '12345678'}
# contacts.insert_one(contact)
#
# print(contacts.find_one({'name': 'test'}))
# print(client.test_database)
# post = {"test": "test"}
# post2 = {"test": "test2", "123": "1234"}
# collection.insert_one(post)
# collection.insert_one(post2)

# print(collection.find_one({'test': 'test2'}))
#
# import mongoengine
#


class Messages(mongoengine.EmbeddedDocument):
    # False - from contact, True - to contact
    to_from = mongoengine.BooleanField(required=True, default=True)
    datetime = mongoengine.StringField(required=True)
    message = mongoengine.StringField(required=True, default='')


class Contacts(mongoengine.Document):
    name = mongoengine.StringField(required=True, unique=True)
    img_base64 = mongoengine.BinaryField()
    msg = mongoengine.ListField(mongoengine.EmbeddedDocumentField(Messages))


class Db:
    def __init__(self, name='test'):
        path_server = os.path.join(os.getcwd(), 'MongoDB', 'Server', '3.6', 'bin', 'mongod.exe')
        path_db = os.path.join(os.getcwd(), 'mng_db')
        subprocess.Popen([path_server, '--dbpath', path_db])
        mongoengine.connect(name)

    @staticmethod
    def add_contact(name, img_base64=None):
        Contacts(name=name, img_base64=img_base64).save()

    @staticmethod
    def add_img(name, img_base64):
        Contacts.objects(name=name).update_one(img_base64=img_base64)

    @staticmethod
    def add_msg(to_from, name, datetime, msg):
        new_msg = Messages(to_from=to_from, datetime=datetime, message=msg)
        Contacts.objects(name=name).update_one(push__msg=new_msg)



if __name__ == '__main__':
    mongoengine.connect('test')
    # Contacts.drop_collection()
    # Contacts(name='MUSEUN', img_base64=b'123456').save()
    # for element in Contacts.objects:
    #         print(element.name)
    db = Db()
    #
    db.add_img('MUSEUN', b'1234567890')
    #
    db.add_msg(to_from=True, name='MUSEUN', datetime=time.ctime(), msg='sdfg, this is test')
    for element in Contacts.objects:
        for msg in element.msg[-10:]:
            print(msg.datetime, msg.message)
