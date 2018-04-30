from client_v3 import Client

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal, QMutex, Qt, QByteArray, QBuffer
from PyQt5.QtGui import QPixmap, QImage
from queue import Queue

import sys
import re
import time

from system.decorators import mute
from system.config import *
from system.image_worker import PictureImage

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
        uic.loadUi('system/gui/chat_test.ui', self)
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
    def set_qt_elements_enabled(self, contacts=True, chat=False, actions=True, smiles=False):
        elemets = []
        if contacts:
            contacts_button = [self.pushDelete, self.pushAdd]
            elemets += contacts_button
        if chat:
            chat_buttons = [self.pushSend, self.pushCancle]
            elemets += chat_buttons
        if actions:
            actions_ = [self.actionItalic, self.actionBold, self.actionUlined, self.actionOpen]
            elemets += actions_
        if smiles:
            smiles_ = [self.actionSmile, self.actionCrazy, self.actionSad]
            elemets += smiles_
        for el in elemets:
            el.setEnabled(True)

    def enable_chat_elements(self):
        self.textChatEdit.setReadOnly(False)
        self.set_qt_elements_enabled(False, True, False, True)

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
        try:
            if self.auth.action_success:
                mute_.lock()
                client.start_client(self.auth.user)
                mute_.unlock()
                self.load_my_image()
                list_of_contacts = client.get_all_contacts()
                self.fill_the_list(list_of_contacts)
        except Exception as e:
            print(e)

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
        try:
            self.get_selected_list_item()
            self.enable_chat_elements()
            self.chatName.setText(self.selected_item_text)
            self.chatDisplay.clear()
            self.load_chat_history()
        except Exception as e:
            print(e)
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
        document = self.parsing_html(self.textChatEdit.toHtml())
        print(document)
        # очищаем строку ввода текста
        self.textChatEdit.clear()
        return document

    def send_message(self):
        doc = self.get_chat_text()
        mute_.lock()
        client.send_msg_message(self.selected_item_text, client.username, doc)
        mute_.unlock()
        self.append_to_text(doc=doc)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def change_style(self, style='italic'):
        if style == 'italic':
            tag = 'i'
        elif style == 'bold':
            tag = 'b'
        elif style == 'underlined':
            tag = 'u'
        text = self.textChatEdit.textCursor().selection()
        text_fragment = self.parsing_fragment(text.toHtml())
        if text_fragment:
            self.textChatEdit.textCursor().insertHtml('<{}>'.format(tag) +
                                                      text_fragment +
                                                      '</{}>'.format(tag))

    def make_italic(self):
        self.change_style()

    def make_bold(self):
        self.change_style('bold')

    def make_under(self):
        self.change_style('underlined')

    @staticmethod
    def parsing_html(text):
        pattern = r';">(.*)</p>'
        res = re.findall(pattern, text)
        return res[0]

    @staticmethod
    def parsing_fragment(text):
        pattern = r'<!--StartFragment-->(.*)<!--EndFragment-->'
        res = re.findall(pattern, text)
        if res:
            return res[0]
        else:
            return None

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def smile(self, smile_type='smile'):
        url = SMILES.get(smile_type, None)
        if url:
            self.textChatEdit.textCursor().insertHtml('<img src="%s" />' % url)

    def reg_smile(self):
        self.smile()

    def sad_smile(self):
        self.smile('sad')

    def crz_smile(self):
        self.smile('crazy')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def image_out_of_byte(self, byte_image=b''):
        if byte_image:
            img_ = QImage.fromData(byte_image, 'PNG')
            pixmap = QPixmap.fromImage(img_)
        else:
            pixmap = None
        return pixmap

    def update_my_image(self, img):
        """
        Обновляется клиентское изображение в базе данных
        """
        if client.client_db.request_image(1):
            client.client_db.update_my_image(img)
        else:
            client.client_db.add_image(img)

    def show_open_f_dialog(self):
        fnames = QFileDialog.getOpenFileName(self, 'Open MY file')
        fname = fnames[0]
        pic = PictureImage(fname, 150, 150)
        self.update_my_image(pic.cropped_bytes_return())
        pixmap = self.image_out_of_byte(pic.cropped_bytes_return())
        self.myLabel.setPixmap(pixmap)

    def load_my_image(self):
        """
        Выгружается клиентское изображение из базы данных
        :return:
        """
        img = client.client_db.request_image(1)
        if img:
            pixmap = self.image_out_of_byte(img.data)
            self.myLabel.setPixmap(pixmap)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def start(self):
        self.actionLogin.triggered.connect(self.auth.action)
        self.actionRegister.triggered.connect(self.reg.action)
        self.auth.notifier.rejected.connect(self.display_contacts)
        self.auth.notifier.rejected.connect(self.receiver_thread_start)
        self.receiver.gotData.connect(self.thread_receiver_handle)
        self.auth.Signal.connect(self.set_qt_elements_enabled)
        self.listContacts.itemDoubleClicked.connect(self.open_a_chat_window)
        self.listContacts.itemClicked.connect(self.get_selected_list_item)
        self.pushAdd.clicked.connect(self.add_item_to_list)
        self.pushDelete.clicked.connect(self.del_item_from_list)
        self.pushSend.clicked.connect(self.send_message)
        self.pushCancle.clicked.connect(self.textChatEdit.clear)
        self.actionItalic.triggered.connect(self.make_italic)
        self.actionBold.triggered.connect(self.make_bold)
        self.actionUlined.triggered.connect(self.make_under)
        self.actionSmile.triggered.connect(self.reg_smile)
        self.actionSad.triggered.connect(self.sad_smile)
        self.actionCrazy.triggered.connect(self.crz_smile)
        self.actionOpen.triggered.connect(self.show_open_f_dialog)


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    client = Client()
    window = ChatWindow()
    window.start()
    window.show()
    sys.exit(app.exec_())

