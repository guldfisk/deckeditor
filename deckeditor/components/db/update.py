from __future__ import annotations

import threading

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog

from mtgorp.db import create
from mtgorp.managejson import download
from mtgorp.managejson.update import check, update_last_updated


class DownloadWorker(threading.Thread):

    def __init__(self, dialog: DBUpdateDialog):
        super().__init__(daemon = True)
        self._dialog = dialog

    def run(self) -> None:
        last_updates = check()
        if last_updates is not None:
            self._dialog.add_log_entry.emit('New magic json')
            download.re_download()
            self._dialog.add_log_entry.emit('New magic json downloaded')
            create.update_database()
            self._dialog.add_log_entry.emit('Database updated')
            update_last_updated(last_updates)
        else:
            self._dialog.add_log_entry.emit('Magic db up to date')

        self._dialog.completed.emit()


class ForceRegenerateWorker(threading.Thread):

    def __init__(self, dialog: DBUpdateDialog):
        super().__init__(daemon = True)
        self._dialog = dialog

    def run(self) -> None:
        create.update_database()
        self._dialog.add_log_entry.emit('Database updated')
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

        self._download_button = QtWidgets.QPushButton('Download and generate')
        self._download_button.clicked.connect(self._download_and_generate)

        self._generate_button = QtWidgets.QPushButton('Generate')
        self._generate_button.clicked.connect(self._generate)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._info_label)
        layout.addWidget(self._log_view)
        layout.addWidget(self._download_button)
        layout.addWidget(self._generate_button)

        self.add_log_entry.connect(self._log)

        self.completed.connect(self.accept)

    def _log(self, text: str) -> None:
        self._log_value += text + '\n'
        self._log_view.setText(self._log_value)

    def _download_and_generate(self) -> None:
        self._download_button.setEnabled(False)
        self._generate_button.setEnabled(False)
        DownloadWorker(self).start()

    def _generate(self):
        self._download_button.setEnabled(False)
        self._generate_button.setEnabled(False)
        ForceRegenerateWorker(self).start()
