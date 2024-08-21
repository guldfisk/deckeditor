import logging
import typing as t

import requests
from cubeclient.endpoints import AsyncNativeApiClient
from cubeclient.models import DbInfo, User
from promise import Promise
from PyQt5.QtCore import QObject, pyqtSignal
from requests import Response

from deckeditor import values
from deckeditor.context.context import Context


class ConnectionException(Exception):
    pass


class LoginController(QObject):
    login_pending = pyqtSignal(str, str)
    login_failed = pyqtSignal(str)
    login_success = pyqtSignal(User, str)
    login_terminated = pyqtSignal()

    def _handle_login_error(self, e: Exception):
        message = "invalid credentials" if isinstance(e, requests.exceptions.HTTPError) else "connection error"
        Context.notification_message.emit(message)
        self.login_failed.emit(message)
        logging.info("Failed login: {}".format(e))
        raise ConnectionException(message)

    def _handle_db_info(self, info: DbInfo, message_success: bool) -> None:
        if info.checksum != Context.db.checksum.hex():
            if info.json_updated_at > Context.db.json_version:
                message = "DB out of date"
            else:
                message = "DB does not match remote"
            Context.notification_message.emit(message)
        elif message_success:
            Context.notification_message.emit("DB up to date with remote")

    def _handle_repo_tags(self, response: Response) -> None:
        if response.json()[0]["name"] != values.VERSION:
            Context.notification_message.emit(f"New version of {values.APPLICATION_NAME} available")

    def _handle_min_client_version(self, min_version: str) -> None:
        if tuple(map(int, values.VERSION.split("."))) < tuple(map(int, min_version.split("."))):
            Context.notification_message.emit(
                "Embargo edit version not supported by server. "
                "Please update to at least {}. (current version: {})".format(
                    min_version,
                    values.VERSION,
                )
            )

    def _handle_login_success(self, v: t.Any) -> t.Any:
        Context.token_changed.emit(Context.cube_api_client.token)
        self.login_success.emit(Context.cube_api_client.user, Context.cube_api_client.host)
        self.validate()
        return v

    def validate(self, message_success: bool = False):
        Context.cube_api_client.db_info().then(lambda i: self._handle_db_info(i, message_success)).catch(
            logging.warning
        )
        Context.cube_api_client.min_client_version().then(self._handle_min_client_version).catch(logging.warning)
        Promise.resolve(
            Context.cube_api_client.executor.submit(
                requests.get,
                values.REPO_TAGS_PATH,
            )
        ).then(
            self._handle_repo_tags,
        ).catch(
            logging.warning,
        )

    def log_out(self):
        Context.cube_api_client.logout()
        Context.token_changed.emit(None)
        self.login_terminated.emit()

    def login(self, host: str, username: str, password: str) -> Promise[t.Any]:
        if (Context.cube_api_client.scheme, Context.cube_api_client.host) != AsyncNativeApiClient.parse_host(host):
            Context.cube_api_client = AsyncNativeApiClient(host, Context.db)

        self.login_pending.emit(username, host)

        return (
            Context.cube_api_client.login(username, password)
            .then(self._handle_login_success)
            .catch(self._handle_login_error)
        )

    def re_login(self) -> None:
        host = Context.settings.value("host_name", "", str)
        username = Context.settings.value("username", "", str)
        password = Context.settings.value("password", "", str)
        if not host or not username or not password:
            return
        self.login(host, username, password)


LOGIN_CONTROLLER = LoginController()
