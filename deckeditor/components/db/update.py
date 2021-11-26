from __future__ import annotations

import os
import threading

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QInputDialog

from mtgorp.db.create import SqlDatabaseCreator
from mtgorp.db.load import DB_PATH
from mtgorp.managejson.update import check_and_update, regenerate_db

from cubeclient.endpoints import download_db_from_remote

from deckeditor.context.context import Context
from deckeditor.context.sql import SqlContext


def update_sql_database(last_json_update):
    if getattr(SqlContext, 'engine', None) is None:
        SqlContext.init(Context.settings)

    SqlDatabaseCreator(
        session_factory = SqlContext.scoped_session,
        engine = SqlContext.engine,
        json_updated_at = last_json_update,
    ).create_database()


class DbWorker(threading.Thread):

    def __init__(self, dialog: DBUpdateDialog):
        super().__init__(daemon = True)
        self._dialog = dialog


class DownloadWorker(DbWorker):

    def run(self) -> None:
        check_and_update(force = True)
        self._dialog.completed.emit()


class CheckAndUpdateSQLWorker(DbWorker):

    def run(self) -> None:
        check_and_update(force = True, updaters = (update_sql_database,))
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
        download_db_from_remote(self._host, DB_PATH, verify=not Context.no_ssl_verify)
        self._dialog.completed.emit()


class DBUpdateDialog(QDialog):
    completed = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle('Update MTG DB')

        self._download_and_generate_button = QtWidgets.QPushButton('Download and generate')
        self._download_and_generate_button.clicked.connect(self._download_and_generate)

        self._download_and_generate_button_sql = QtWidgets.QPushButton('Download and generate SQL')
        self._download_and_generate_button_sql.clicked.connect(self._download_and_generate_sql)

        self._generate_button = QtWidgets.QPushButton('Generate')
        self._generate_button.clicked.connect(self._generate)

        self._download_button = QtWidgets.QPushButton('Download')
        self._download_button.clicked.connect(self._download)

        self._buttons = (
            self._download_and_generate_button,
            self._download_and_generate_button_sql,
            self._generate_button,
            self._download_button,
        )

        layout = QtWidgets.QVBoxLayout(self)

        for button in self._buttons:
            layout.addWidget(button)

        self.completed.connect(self.accept)

        self._download_button.setFocus()

    def set_enabled(self, enabled: bool) -> None:
        for button in self._buttons:
            button.setEnabled(enabled)

    def _download_and_generate_sql(self) -> None:
        self.setEnabled(False)
        CheckAndUpdateSQLWorker(self).start()

    def _download_and_generate(self) -> None:
        self.setEnabled(False)
        DownloadWorker(self).start()

    def _generate(self) -> None:
        self.setEnabled(False)
        ForceRegenerateWorker(self).start()

    def _download(self) -> None:
        host, success = QInputDialog.getText(
            self,
            'Choose Host',
            '',
            text = 'prohunterdogkeeper.dk',
        )
        if success:
            self.setEnabled(False)
            DownloadFromRemoteWorker(self, host = host).start()
