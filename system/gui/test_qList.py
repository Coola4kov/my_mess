import sys
from PyQt5 import QtWidgets

app = QtWidgets.QApplication(sys.argv)

listWidget = QtWidgets.QListWidget()

for i in range(10):
    item = QtWidgets.QListWidgetItem("Item %i" % i)
    listWidget.addItem(item)

listWidget.show()
sys.exit(app.exec_())