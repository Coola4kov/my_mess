from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
import sys


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi('chat.ui', self)
        # позволяет отсортировать отображаемый список
        self.listContacts.setSortingEnabled(True)
        self.selected_item_row = None
        self.selected_item_text = ""

    def get_text(self):
        try:
            # забираем данные из строки ввода текста
            document = self.textChatEdit.toPlainText()
            # очищаем строку ввода текста
            self.clear_edit_window()
            print(document)
        except Exception as e:
            print(e)

    def clear_edit_window(self):
        # очищаем строку ввода текста
        self.textChatEdit.clear()

    def fill_the_list(self, list_):
        for i in list_:
            self.listContacts.addItem(QtWidgets.QListWidgetItem("{}".format(i)))
        # сортируем введённый текст
        self.listContacts.sortItems()

    def get_selected_item(self):
        self.selected_item_text = self.listContacts.currentItem().text()
        self.selected_item_row = self.listContacts.currentRow()
        print(self.selected_item_text)

    def add_item(self):
        # добавление элемент в список
        text, ok = QtWidgets.QInputDialog.getText(self, 'Добавить пользователя', 'Введите имя пользователя:')
        if ok:
            self.listContacts.addItem(QtWidgets.QListWidgetItem(str(text)))
            self.listContacts.sortItems()

    def delete_selected_item(self):
        try:
            # Диалоговое окно
            button_reply = QMessageBox.question(self, 'Удаление пользователя',
                                                'Вы хотите удалить {}'.format(self.selected_item_text),
                                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if button_reply == QMessageBox.Yes:
                self.listContacts.takeItem(self.selected_item_row)
                print('Yes clicked.')
            else:
                print('No clicked.')
        except Exception as e:
            print(e)

    def main_cycle(self):
        self.pushSend.clicked.connect(self.get_text)
        self.pushCancle.clicked.connect(self.clear_edit_window)
        self.actionLogin.triggered.connect(lambda: self.fill_the_list(['b', 'a', 'z', 't', 'e']))
        self.listContacts.itemClicked.connect(self.get_selected_item)
        self.pushDelete.clicked.connect(self.delete_selected_item)
        self.pushAdd.clicked.connect(self.add_item)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = ChatWindow()
    window.main_cycle()
    window.show()
    sys.exit(app.exec_())
