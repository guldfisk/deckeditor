from PyQt5 import QtWidgets

from deckeditor.authentication import login
from deckeditor.context.context import Context


class LoginDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self._ok_button = QtWidgets.QPushButton('Ok', self)

        self._host_selector_label = QtWidgets.QLabel('host')
        self._host_selector = QtWidgets.QLineEdit()
        self._host_selector.setText(
            Context.settings.value('host_name', 'localhost:7000')
        )

        self._username_selector_label = QtWidgets.QLabel('username')
        self._username_selector = QtWidgets.QLineEdit()
        self._username_selector.setText(
            Context.settings.value('username', 'root')
        )

        self._password_selector_label = QtWidgets.QLabel('password')
        self._password_selector = QtWidgets.QLineEdit()
        self._password_selector.setEchoMode(QtWidgets.QLineEdit.Password)
        self._password_selector.setText(
            Context.settings.value('password', 'fraekesteguyaround')
        )

        self._top_box = QtWidgets.QVBoxLayout()
        self._bottom_box = QtWidgets.QHBoxLayout()

        self._top_box.addWidget(self._host_selector_label)
        self._top_box.addWidget(self._host_selector)
        self._top_box.addWidget(self._username_selector_label)
        self._top_box.addWidget(self._username_selector)
        self._top_box.addWidget(self._password_selector_label)
        self._top_box.addWidget(self._password_selector)

        self._bottom_box.addWidget(self._ok_button)

        self._layout = QtWidgets.QVBoxLayout()

        self._layout.addLayout(self._top_box)
        self._layout.addLayout(self._bottom_box)

        self.setLayout(self._layout)

        self._ok_button.clicked.connect(self._create)

    def _create(self) -> None:
        host_name = self._host_selector.text()
        username = self._username_selector.text()
        password = self._password_selector.text()

        login.login(host_name, username, password)

        Context.settings.setValue('host_name', host_name)
        Context.settings.setValue('username', username)
        Context.settings.setValue('password', password)

        self.accept()
