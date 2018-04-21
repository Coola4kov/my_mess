from client_v3 import Client

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal,  QMutex
from queue import Queue

import sys
import time

from system.config import *

# client_db = ClientWorker('sqlite:///system/db/client_db.db')
client = Client()
mute_ = QMutex()
que = Queue()


def mute(func):
    def decorator(*args, **kwargs):
        mute_.lock()
        res = func(*args, **kwargs)
        mute_.unlock()
        return res
    return decorator


class AuthWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('system/gui/login.ui', self)
        self.user = ""
        self.pass_ = ""

    def get_username(self):
        self.user = self.username.text()
        self.pass_ = self.password.text()
        print(self.user, self.pass_)


class ReceiverHandler(QObject):
    gotData = pyqtSignal()
    finished = pyqtSignal(int)

    def __init__(self, sock):
        super().__init__()
        self.sock = sock
        self.is_active = False

    def poll(self):
        self.is_active = True
        while self.is_active:
            mute_.lock()
            try:
                sock.settimeout(0.5)
                data = client.m_r.rcv_message(self.sock)
                if data.get(ACTION) == MSG:
                    self.gotData.emit()
            except:
                pass
            sock.settimeout(None)
            mute_.unlock()


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self, sock, parent=None):
        super().__init__(parent)
        uic.loadUi('system/gui/chat.ui', self)
        # позволяет отсортировать отображаемый список
        self.listContacts.setSortingEnabled(True)
        self.selected_item_row = None
        self.selected_item_text = ""
        self.receiver = ReceiverHandler(sock)
        self.thread = QThread()
        self.receiver_start()
        self.auth = AuthWindow()

    def receiver_start(self):
        self.receiver.moveToThread(self.thread)
        self.thread.started.connect(self.receiver.poll)
        self.thread.start()

    @pyqtSlot()
    def sygnal_handle(self):
        chat_name = client.m_r.dict_message[FROM]
        doc = client.m_r.dict_message[MESSAGE]
        # print(chat_name, doc
        if self.selected_item_text == chat_name:
            self.append_to_text(chat_name=chat_name, doc=doc)
        client.client_db.session.rollback()
        client.client_db.add_to_history(chat_name, time.ctime(),
                                        doc, False)

    def fill_the_list(self, list_):
        for i in list_:
            self.listContacts.addItem(QtWidgets.QListWidgetItem("{}".format(i)))
        # сортируем введённый текст
        self.listContacts.sortItems()

    def get_selected_item(self):
        self.selected_item_text = self.listContacts.currentItem().text()
        self.selected_item_row = self.listContacts.currentRow()

    def chat(self):
        self.get_selected_item()
        self.chatName.setText(self.selected_item_text)
        self.clear_chat_window()
        history = reversed(client.load_messages_from_history(self.selected_item_text))
        for m in history:
            if m['to_from']:
                chat_name = 'Me'
            else:
                chat_name = self.selected_item_text
            self.append_to_text(m['timestamp'], chat_name, m['message'])

    def login(self, sock, username='basic_user'):
        mute_.lock()
        self.auth.setEnabled(True)
        self.auth.show()
        try:
            client.start_client(sock, username)
            contacts = client.get_all_contacts()
            print(contacts)
            self.fill_the_list(contacts)
        except Exception as e:
            print(e)
        mute_.unlock()

    @mute
    def add_item(self, sock):
        text, ok = QtWidgets.QInputDialog.getText(self, 'Добавить пользователя', 'Введите имя пользователя:')
        if ok and text:
            if client.check_local_contact(text):
                if client.change_contact_global(sock, text):
                    client.add_contact_local(text)
                    self.listContacts.addItem(QtWidgets.QListWidgetItem(str(text)))
                    self.listContacts.sortItems()
            else:
                pass

    @mute
    def del_item(self, sock):
        # Диалоговое окно
        button_reply = QMessageBox.question(self, 'Удаление пользователя',
                                            'Вы хотите удалить {}'.format(self.selected_item_text),
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if button_reply == QMessageBox.Yes:
            if not client.check_local_contact(self.selected_item_text):
                if client.change_contact_global(sock, self.selected_item_text, False):
                    client.del_contact_local(self.selected_item_text)
                    self.listContacts.takeItem(self.selected_item_row)
        else:
            pass

    def get_chat_text(self):
        try:
            # забираем данные из строки ввода текста
            document = self.textChatEdit.toPlainText()
            # очищаем строку ввода текста
            self.clear_edit_window()
            return document
        except Exception as e:
            print(e)

    def append_to_text(self, time_=None, chat_name='Me', doc=''):
        if time_ is None:
            time_ = time.ctime()
        # if self.selected_item_text:
        self.chatDisplay.append("{} [{}]: {}\n".format(time_, chat_name, doc))

    def send_message(self, sock):
        mute_.lock()
        doc = self.get_chat_text()
        client.send_msg_message(sock, self.selected_item_text, client.username, doc)
        self.append_to_text(doc=doc)
        mute_.unlock()

    def clear_edit_window(self):
        self.textChatEdit.clear()

    def clear_chat_window(self):
        self.chatDisplay.clear()


if __name__ == '__main__':
    #TODO сделать окно авторищации
    app = QtWidgets.QApplication(sys.argv)
    sock = client.open_client_socket()
    window = ChatWindow(sock)
    window.actionLogin.triggered.connect(lambda: window.login(sock, 'MUSEUN'))
    window.listContacts.itemDoubleClicked.connect(window.chat)
    window.listContacts.itemClicked.connect(window.get_selected_item)
    window.pushAdd.clicked.connect(lambda: window.add_item(sock))
    window.pushSend.clicked.connect(lambda: window.send_message(sock))
    window.pushDelete.clicked.connect(lambda: window.del_item(sock))
    window.receiver.gotData.connect(window.sygnal_handle)
    window.show()
    sys.exit(app.exec_())


