from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, ForeignKey, BLOB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
Base = declarative_base()


# Классы для работы с клиентской базой данных
class Contacts(Base):
    """
    Класс обеспечивающий доступ к таблице contacts в клиентской базе данных
    """
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, unique=True)
    # Переменная возвращающая все связные строки в таблице message_history
    message_history = relationship('MessageHistory', back_populates="contact")
    image_id = Column(Integer, ForeignKey('image.id'), default=1)
    image = relationship('Image', back_populates='contact')

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<contact ({})>'.format(self.name)


class MessageHistory(Base):
    """
    Класс для доступа к таблице message_history в клиентской базе данных
    """
    __tablename__ = 'message_history'
    id = Column(Integer, primary_key=True, unique=True)
    to_from = Column(Integer)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    timestamp = Column(Integer)
    message = Column(String)
    contact = relationship("Contacts", back_populates="message_history")

    def __init__(self, contact, timestamp, message, to_from=True):
        self.to_from = to_from
        # self.contact_id = contact_id
        self.timestamp = timestamp
        self.message = message
        self.contact = contact

    def __repr__(self):
        return '<message_history ({} {} {} {})>'.format(self.to_from, self.contact_id, self.timestamp, self.message)


class Image(Base):
    __tablename__ = 'image'
    id = Column(Integer, primary_key=True)
    data = Column(BLOB)
    contact = relationship('Contacts', back_populates='image')

    def __init__(self, img):
        self.data = img


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


class ClientWorker(DbWorker):
    """
    Класс для работы с клиентской базой данных
    """
    def request_contact(self, contact_name):
        """
        Поиск первого найденного имени контакта
        :param contact_name: string имя контакта
        :return: найденный контакт класса Client
        """
        try:
            contact = self.session.query(Contacts).filter(Contacts.name == contact_name).one()
            # print(contact)
        except NoResultFound:
            contact = None
        return contact

    def add_to_history(self, contact_name, timestamp, message, to_from):
        """
        Добавление к таблице message_history запись о пришедшем сообдении, если найденного контакта нет
        в таблице contacts клиентской базы данных, то вызывается метод change_contact_global и контакт добавляется в таблицу
        :param contact_name: string имя контакта
        :param timestamp: целое значени временной метки
        :param message: сообщение в формате string
        :param to_from: true - от контакта клиенту, false - от клиента контакту
        :return:
        """
        contact = self.request_contact(contact_name)
        if contact is None:
            self.add_contact(contact_name)
            contact = self.request_contact(contact_name)
        new_history = MessageHistory(contact, timestamp, message, to_from)
        self.session.add(new_history)
        self.commit_session()

    def get_messages_from_history(self, contact_name):
        contact = self.request_contact(contact_name)
        history_message = [{'timestamp': h_message.timestamp,
                            'message': h_message.message,
                            'to_from':h_message.to_from}
                           for h_message in self.session.query(MessageHistory).
                               filter(MessageHistory.contact == contact).
                               order_by(MessageHistory.id.desc()).limit(15)]
        return history_message

    def get_all_contacts(self):
        contacts = [contact.name for contact in self.session.query(Contacts).all()]
        return contacts

    def drop_all_contacts(self):
        self.session.query(Contacts).delete()
        self.commit_session()

    def request_image(self, id=1):
        try:
            img = self.session.query(Image).filter(Image.id == id).one()
        except NoResultFound:
            img = None
        return img

    def add_image(self, byte_image=b''):
        if byte_image:
            new_image = Image(byte_image)
            self.session.add(new_image)
            self.commit_session()

    def update_my_image(self, byte_image=b''):
        if byte_image:
            img = self.request_image(1)
            img.data = byte_image
            self.commit_session()

    def add_contact(self, name):
        """
        Метод содающие запись в таблице contacts клиентской базы данных
        :param name: string имя контакта, от которого пришло сообщение.
        :return:
        """
        if not self.request_contact(name):
            new_contact = Contacts(name)
            self.session.add(new_contact)
            self.commit_session()

    def del_contact(self, name):
        try:
            contact = self.request_contact(name)
            self.session.delete(contact)
            self.commit_session()
        except NoResultFound:
            print('Клиент уже удалён')


if __name__ == '__main__':
    # test = ServerWorker('sqlite:///server_db.db')
    # test.add_to_history("MUSEUN", 3333555648, "192.168.1.2")
    # test.commit_session()
    # engine = create_engine('sqlite:///client_db.db')
    # Session = sessionmaker(bind=engine)
    # session = Session()
    # print(contact)
    # new_contact = Contacts("Victor")
    # session.add(new_contact)
    # session.commit()
    test_client = ClientWorker('sqlite:///mom_client_db.db')
    test_client.add_contact('MUSEUN')
    test_client.add_to_history('MUSEUQN', 123456789, 'Привет, как твои дела?', True)
    test_client.commit_session()
    print(test_client.get_all_contacts())
