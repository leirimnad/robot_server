import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("resources/robot_server_main_window.ui", self)
        self.app_name_label.setText("Robot Server")


app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()