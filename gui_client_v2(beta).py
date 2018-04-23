from client_v3 import Client

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal,  QMutex, Qt
from queue import Queue

import sys
import time

from system.decorators import mute
from system.config import *

mute_ = QMutex()


class Notifier(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('system/gui/authNotifier.ui', self)

    def display_text(self, text, to_do, title, dialog=False):
        self.buttonBox.close()
        self.label.setText(text)
        self.label_2.setText(to_do)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)
        if dialog:
            self.buttonBox.show()
        self.show()


class AuthReg(QtWidgets.QDialog):
    Signal = pyqtSignal()

    def __init__(self, parent=None, auth=True):
        super().__init__(parent)
        uic.loadUi('system/gui/login.ui', self)
        self.user = ""
        self.pass_ = ""
        self.notifier = Notifier()
        self.action_success = False
        self.buttonBox.accepted.connect(self.action_request)
        self.Signal.connect(self.action_notification)
        self.notifier.buttonBox.accepted.connect(self.action)
        self.notifier.buttonBox.accepted.connect(self.notifier.close)
        self.notifier.buttonBox.rejected.connect(self.notifier.close)
        if auth:
            self.action_func = client.authorization
            self.action_text = 'Авторизация'
        else:
            self.action_func = client.registration
            self.action_text = 'Регистрация'

    def clear_text_fields(self):
        self.username.clear()
        self.password.clear()

    def get_credentials(self):
        self.user = self.username.text()
        self.pass_ = self.password.text()

    @mute(mute_)
    def action_request(self):
        self.get_credentials()
        # заглушка, должна вызываться авторизация.
        if self.action_func(self.user, self.pass_):
            self.action_success = True
        else:
            self.action_success = False
        self.Signal.emit()
        self.clear_text_fields()

    def action(self):
        self.show()

    @pyqtSlot()
    def action_notification(self):
        if self.action_success:
            print('Я выполняюсь')
            self.notifier.display_text('{} успешна'.format(self.action_text),
                                       'Приятного пользования',
                                       self.action_text)
        else:
            self.notifier.display_text('{} не успешна'.format(self.action_text),
                                       'Попробуйте ещё раз',
                                       self.action_text, True)


class ReceiverHandler(QObject):
    gotData = pyqtSignal()
    finished = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.is_active = False

    def poll(self):
        self.is_active = True
        while self.is_active:
            try:
                mute_.lock()
                client.sock.settimeout(0.5)
                data = client.m_r.rcv_message(client.sock)
                if data.get(ACTION) == MSG:
                    print('Got a message')
                    self.gotData.emit()
            except:
                pass
            client.sock.settimeout(None)
            mute_.unlock()


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('system/gui/chat.ui', self)
        self.listContacts.setSortingEnabled(True)
        self.selected_item_row = None
        self.selected_item_text = ""
        self.notifier = Notifier()
        self.receiver = ReceiverHandler()
        self.thread = QThread()
        self.auth = AuthReg()
        self.reg = AuthReg(auth=False)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @pyqtSlot()
    def set_buttons_enabled(self):
        for el in [self.pushDelete, self.pushAdd, self.pushSend, self.pushCancle]:
            el.setEnabled(True)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def receiver_thread_start(self):
        self.receiver.moveToThread(self.thread)
        self.thread.started.connect(self.receiver.poll)
        self.thread.start()

    @pyqtSlot()
    def thread_receiver_handle(self):
        chat_name = client.m_r.dict_message[FROM]
        doc = client.m_r.dict_message[MESSAGE]
        # print(chat_name, doc
        if self.selected_item_text == chat_name:
            self.append_to_text(chat_name=chat_name, doc=doc)
        client.client_db.session.rollback()
        client.client_db.add_to_history(chat_name, time.ctime(),
                                        doc, False)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def fill_the_list(self, list_):
        for i in list_:
            self.listContacts.addItem(QtWidgets.QListWidgetItem("{}".format(i)))
        # сортируем введённый текст
        self.listContacts.sortItems()

    def display_contacts(self):
        if self.auth.action_success:
            mute_.lock()
            client.start_client(self.auth.user)
            mute_.unlock()
            list_of_contacts = client.get_all_contacts()
            self.fill_the_list(list_of_contacts)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_selected_list_item(self):
        self.selected_item_text = self.listContacts.currentItem().text()
        self.selected_item_row = self.listContacts.currentRow()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def append_to_text(self, time_=None, chat_name='Me', doc=''):
        if time_ is None:
            time_ = time.ctime()
        self.chatDisplay.append("{} [{}]: {}\n".format(time_, chat_name, doc))


    def load_chat_history(self):
        history = reversed(client.load_messages_from_history(self.selected_item_text))
        for m in history:
            if m['to_from']:
                chat_name = 'Me'
            else:
                chat_name = self.selected_item_text
            self.append_to_text(m['timestamp'], chat_name, m['message'])

    def open_a_chat_window(self):
        self.get_selected_list_item()
        self.chatName.setText(self.selected_item_text)
        self.chatDisplay.clear()
        self.load_chat_history()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def add_item_to_list(self):
        text, ok = QtWidgets.QInputDialog.getText(self, 'Добавить пользователя', 'Введите имя пользователя:')
        if ok and text:
            if client.check_local_contact(text):
                self.notifier.display_text('{} уже в контактах'.format(text), 'Найдите ещё одного друга',
                                           'Добавление')
            else:
                mute_.lock()
                if not client.change_contact_global(text):
                    self.notifier.display_text('Действие не удалось', 'Попробуйте ещё раз',
                                               "Добавление")
                else:
                    client.add_contact_local(text)
                    self.listContacts.addItem(QtWidgets.QListWidgetItem(str(text)))
                    self.listContacts.sortItems()
                mute_.unlock()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def del_item_from_list(self):
        button_reply = QMessageBox.question(self, 'Удаление пользователя',
                                            'Вы хотите удалить {}'.format(self.selected_item_text),
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if button_reply == QMessageBox.Yes:
            if not client.check_local_contact(self.selected_item_text):
                self.notifier.display_text('{} уже нет в контактах'.format(self.selected_item_text),
                                           'Чтобы удалить, нужно подружиться', 'Удаление')
            else:
                mute_.lock()
                if not client.change_contact_global(self.selected_item_text, False):
                    self.notifier.display_text('Действие не удалось', 'Попробуйте ещё раз',
                                               "Добавление")
                else:
                    client.del_contact_local(self.selected_item_text)
                    self.listContacts.takeItem(self.selected_item_row)
                mute_.unlock()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_chat_text(self):
        # забираем данные из строки ввода текста
        document = self.textChatEdit.toPlainText()
        # document = self.textChatEdit.toHtml()
        # очищаем строку ввода текста
        self.textChatEdit.clear()
        return document

    def send_message(self):
        doc = self.get_chat_text()
        mute_.lock()
        client.send_msg_message(self.selected_item_text, client.username, doc)
        mute_.unlock()
        self.append_to_text(doc=doc)

    def action_italic(self):
        pass

    def make_italic(self):
        text = self.textChatEdit.textCursor().selectedText()
        print(text)
        self.textChatEdit.textCursor().insertHtml('<i>' + text + '</i>')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def start(self):
        self.actionLogin.triggered.connect(self.auth.action)
        self.actionRegister.triggered.connect(self.reg.action)
        self.auth.notifier.rejected.connect(self.display_contacts)
        self.auth.notifier.rejected.connect(self.receiver_thread_start)
        self.receiver.gotData.connect(self.thread_receiver_handle)
        self.auth.Signal.connect(self.set_buttons_enabled)
        self.listContacts.itemDoubleClicked.connect(self.open_a_chat_window)
        self.listContacts.itemClicked.connect(self.get_selected_list_item)
        self.pushAdd.clicked.connect(self.add_item_to_list)
        self.pushDelete.clicked.connect(self.del_item_from_list)
        self.pushSend.clicked.connect(self.send_message)
        self.pushCancle.clicked.connect(self.textChatEdit.clear)
        self.actionItalic.triggered.connect(self.make_italic)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    client = Client()
    window = ChatWindow()
    window.start()
    window.show()
    sys.exit(app.exec_())

