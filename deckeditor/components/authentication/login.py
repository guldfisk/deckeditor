from PyQt5 import QtWidgets

from deckeditor.authentication.login import LOGIN_CONTROLLER
from deckeditor.context.context import Context


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self._ok_button = QtWidgets.QPushButton("Ok", self)

        self._host_selector_label = QtWidgets.QLabel("host")
        self._host_selector = QtWidgets.QLineEdit()
        self._host_selector.setText(Context.settings.value("host_name", "prohunterdogkeeper.dk"))

        self._username_selector_label = QtWidgets.QLabel("username")
        self._username_selector = QtWidgets.QLineEdit()
        self._username_selector.setText(Context.settings.value("username", ""))

        self._password_selector_label = QtWidgets.QLabel("password")
        self._password_selector = QtWidgets.QLineEdit()
        self._password_selector.setEchoMode(QtWidgets.QLineEdit.Password)
        self._password_selector.setText(Context.settings.value("password", ""))

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

    def set_enabled(self, enabled: bool) -> None:
        self._host_selector.setEnabled(enabled)
        self._username_selector.setEnabled(enabled)
        self._password_selector.setEnabled(enabled)

    def _on_login_success(self, value) -> None:
        Context.settings.setValue("host_name", self._host_selector.text())
        Context.settings.setValue("username", self._username_selector.text())
        Context.settings.setValue("password", self._password_selector.text())
        self.set_enabled(True)

    def _create(self) -> None:
        host_name = self._host_selector.text()
        username = self._username_selector.text()
        password = self._password_selector.text()

        self.set_enabled(False)

        LOGIN_CONTROLLER.log_out()
        LOGIN_CONTROLLER.login(host_name, username, password).then(self._on_login_success).catch(
            lambda e: self.set_enabled(True),
        )
        self.accept()
