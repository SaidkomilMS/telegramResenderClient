from pyrogram import Client
from pyrogram.errors.exceptions.unauthorized_401 import SessionPasswordNeeded
from PySide2.QtWidgets import (
    QMainWindow, QPushButton, QLabel, QLineEdit, QApplication,
)

from window import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        API_ID = 2096979
        API_HASH = '2bb5d66a4618e7325a91aab04d22c071'
        self.client = Client("newsession", API_ID, API_HASH)
        self.client.connect()
        self.pushButton.clicked.connect(self.send_code)
        self.pushButton_2.clicked.connect(self.check_code)
        self.pushButton_3.clicked.connect(self.check_password)
        self.show()

    def send_code(self):
        self.phone_number = self.lineEdit.text()
        self.sent_code = self.client.send_code(self.phone_number)
        self.pushButton_2.setEnabled(True)
        self.lineEdit_2.setEnabled(True)
        self.pushButton_3.setEnabled(False)
        self.lineEdit_3.setEnabled(False)

    def check_code(self):
        code = self.lineEdit_2.text()
        try:
            self.client.sign_in(self.phone_number, self.sent_code.phone_code_hash, code)
        except SessionPasswordNeeded:
            self.pushButton_3.setEnabled(True)
            self.lineEdit_3.setEnabled(True)
            password_hint = self.client.get_password_hint()
            self.lineEdit_3.setPlaceholderText(password_hint)
        else:
            self.close()

    def check_password(self):
        try:
            self.client.check_password(self.lineEdit_3.text())
        except Exception as e:
            pass
        else:
            self.close()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mw = MainWindow()
    sys.exit(app.exec_())
