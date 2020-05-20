from __future__ import annotations

import os
import threading

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QInputDialog

from mtgorp.db.load import DB_PATH
from mtgorp.managejson.update import check_and_update, regenerate_db

from cubeclient.endpoints import download_db_from_remote


class DbWorker(threading.Thread):

    def __init__(self, dialog: DBUpdateDialog):
        super().__init__(daemon = True)
        self._dialog = dialog


class DownloadWorker(DbWorker):

    def run(self) -> None:
        check_and_update(force = True)
        self._dialog.completed.emit()


class ForceRegenerateWorker(DbWorker):

    def run(self) -> None:
        regenerate_db(force = True)
        self._dialog.completed.emit()


class DownloadFromRemoteWorker(DbWorker):

    def __init__(self, dialog: DBUpdateDialog, host: str):
        super().__init__(dialog)
        self._host = host

    def run(self) -> None:
        os.makedirs(os.path.join(*os.path.split(DB_PATH)[:-1]), exist_ok = True)
        download_db_from_remote(self._host, DB_PATH)
        self._dialog.add_log_entry.emit('Database downloaded')
        self._dialog.completed.emit()


class DBUpdateDialog(QDialog):
    add_log_entry = pyqtSignal(str)
    completed = pyqtSignal()

    def __init__(self):
        super().__init__()

        self._info_label = QtWidgets.QLabel('Rebuild database')

        self._log_value = ''
        self._log_view = QtWidgets.QTextEdit()
        self._log_view.setReadOnly(True)

        self._download_and_generate_button = QtWidgets.QPushButton('Download and generate')
        self._download_and_generate_button.clicked.connect(self._download_and_generate)

        self._generate_button = QtWidgets.QPushButton('Generate')
        self._generate_button.clicked.connect(self._generate)

        self._download_button = QtWidgets.QPushButton('Download')
        self._download_button.clicked.connect(self._download)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._info_label)
        layout.addWidget(self._log_view)
        layout.addWidget(self._download_and_generate_button)
        layout.addWidget(self._generate_button)
        layout.addWidget(self._download_button)

        self.add_log_entry.connect(self._log)

        self.completed.connect(self.accept)

    def _log(self, text: str) -> None:
        self._log_value += text + '\n'
        self._log_view.setText(self._log_value)

    def _download_and_generate(self) -> None:
        self._download_and_generate_button.setEnabled(False)
        self._generate_button.setEnabled(False)
        DownloadWorker(self).start()

    def _generate(self) -> None:
        self._download_and_generate_button.setEnabled(False)
        self._generate_button.setEnabled(False)
        ForceRegenerateWorker(self).start()

    def _download(self) -> None:
        host, success = QInputDialog.getText(
            self,
            'Choose Host',
            '',
            text = 'prohunterdogkeeper.dk',
        )
        if success:
            self._download_and_generate_button.setEnabled(False)
            self._generate_button.setEnabled(False)
            DownloadFromRemoteWorker(self, host = host).start()
