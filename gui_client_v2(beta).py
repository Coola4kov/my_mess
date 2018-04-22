from client_v3 import Client

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal,  QMutex, Qt
from queue import Queue

import sys
import time

from system.config import *


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
        # self.buttonBox.setEnabled(dialog)
        self.show()


class AuthWindow(QtWidgets.QDialog):
    authSignal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('system/gui/login.ui', self)
        self.user = ""
        self.pass_ = ""
        self.authorized = False
        self.notifier = Notifier()

    def auth_request(self):
        self.user = self.username.text()
        self.pass_ = self.password.text()
        # заглушка, должна вызываться авторизация.
        if client.authorization(self.user, self.pass_):
            self.authorized = True
        else:
            self.authorized = False
        self.authSignal.emit()
        self.buttonBox.accepted.disconnect(self.auth_request)
        # self.notifier.rejected.disconnect(self.authorize)
        self.username.clear()
        self.password.clear()

    def authorize(self):
        self.show()
        # self.setEnabled(True)
        self.buttonBox.accepted.connect(self.auth_request)
        self.authSignal.connect(self.auth_notification)

    @pyqtSlot()
    def auth_notification(self):
        try:
            if self.authorized:
                print('Я выполняюсь')
                self.notifier.display_text('Вы успешно авторизованы', 'Приятного пользования', 'Авторизация')
            else:
                self.notifier.display_text('Вы не авторизованы', 'Попробуйте ещё раз', 'Авторизация', True)
                self.notifier.buttonBox.accepted.connect(self.authorize)
                self.notifier.buttonBox.accepted.connect(self.notifier.close)
                self.notifier.buttonBox.rejected.connect(self.notifier.close)
            # self.authorize()
        except Exception as e:
            print(e)


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('system/gui/chat.ui', self)
        self.listContacts.setSortingEnabled(True)
        self.selected_item_row = None
        self.selected_item_text = ""
        self.auth = AuthWindow()

    def start(self):
        self.actionLogin.triggered.connect(self.auth.authorize)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    client = Client()
    window = ChatWindow()
    window.start()
    window.show()
    sys.exit(app.exec_())

