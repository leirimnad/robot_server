import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic


class ThreadWidget(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("resources/thread_widget.ui", self)


app = QtWidgets.QApplication(sys.argv)
window = ThreadWidget()
window.show()
app.exec_()