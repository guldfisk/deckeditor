import logging
import typing as t

import requests

from PyQt5.QtCore import QObject, pyqtSignal

from promise import Promise

from cubeclient.endpoints import AsyncNativeApiClient
from cubeclient.models import User, DbInfo

from deckeditor.context.context import Context


class ConnectionException(Exception):
    pass


class LoginController(QObject):
    login_pending = pyqtSignal(str, str)
    login_failed = pyqtSignal(str)
    login_success = pyqtSignal(User, str)
    login_terminated = pyqtSignal()

    def _handle_login_error(self, e: Exception):
        message = (
            'invalid credentials'
            if isinstance(e, requests.exceptions.HTTPError) else
            'connection error'
        )
        Context.notification_message.emit(message)
        self.login_failed.emit(message)
        logging.info('Failed login: {}'.format(e))
        raise ConnectionException(message)

    def _handle_db_info(self, info: DbInfo, message_success: bool) -> None:
        if info.checksum != Context.db.checksum.hex():
            if info.json_updated_at > Context.db.json_version:
                message = 'DB out of date'
            else:
                message = 'DB does not match remote'
            Context.notification_message.emit(message)
        elif message_success:
            Context.notification_message.emit('DB up to date with remote')

    def _handle_login_success(self, v: t.Any) -> t.Any:
        Context.token_changed.emit(Context.cube_api_client.token)
        self.login_success.emit(Context.cube_api_client.user, Context.cube_api_client.host)
        self.validate()
        return v

    def validate(self, message_success: bool = False):
        Context.cube_api_client.db_info().then(lambda i: self._handle_db_info(i, message_success))

    def log_out(self):
        Context.cube_api_client.logout()
        Context.token_changed.emit(None)
        self.login_terminated.emit()

    def login(self, host: str, username: str, password: str) -> Promise[t.Any]:
        if Context.cube_api_client.host != host:
            Context.cube_api_client = AsyncNativeApiClient(host, Context.db)

        self.login_pending.emit(username, host)

        return Context.cube_api_client.login(username, password).then(
            self._handle_login_success
        ).catch(
            self._handle_login_error
        )

    def re_login(self) -> None:
        host = Context.settings.value('host_name', '', str)
        username = Context.settings.value('username', '', str)
        password = Context.settings.value('password', '', str)
        if not host or not username or not password:
            return
        self.login(host, username, password)


LOGIN_CONTROLLER = LoginController()
