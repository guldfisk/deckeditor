from __future__ import annotations

import typing as t

from PyQt5.QtCore import QObject, pyqtSignal

from frozendict import frozendict

from lobbyclient.client import LobbyClient, Lobby
from lobbyclient.model import LobbyOptions

from deckeditor.context.context import Context
from deckeditor.store.models import GameTypeOptions


class _LobbyClient(LobbyClient):

    def __init__(self, model: LobbyModelClientConnection, url: str, token: str):
        super().__init__(url, token)
        self._model = model

    def _lobbies_changed(
        self,
        created: t.Mapping[str, Lobby] = frozendict(),
        modified: t.Mapping[str, Lobby] = frozendict(),
        closed: t.AbstractSet[str] = frozenset(),
    ) -> None:
        self._model.changed.emit()

    def _on_error(self, error):
        super()._on_error(error)
        self._model.on_disconnected()

    def _on_client_error(self, message: t.Mapping[str, t.Any]) -> None:
        message = message.get('message')
        if message is not None:
            Context.notification_message.emit(message)

    def _on_close(self):
        super()._on_close()

    def _game_started(self, lobby: Lobby, key: str) -> None:
        if lobby.game_type == 'sealed':
            Context.sealed_started.emit(int(key), True)
        elif lobby.game_type == 'draft':
            Context.draft_started.emit(key)


class LobbyModelClientConnection(QObject):
    changed = pyqtSignal()
    connected = pyqtSignal(bool)

    def __init__(self, parent: t.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._lobby_client: t.Optional[LobbyClient] = None

        if Context.cube_api_client.token:
            self._on_token_changed(None)

        Context.token_changed.connect(self._on_token_changed)

    @property
    def is_connected(self) -> bool:
        return self._lobby_client is not None

    def on_disconnected(self):
        self._lobby_client = None
        self.connected.emit(False)
        self.changed.emit()

    def _on_token_changed(self, token: t.Optional[str]):
        if self._lobby_client is not None:
            self._lobby_client.close()
            self.on_disconnected()

        if not token:
            return

        self._lobby_client = _LobbyClient(
            self,
            url = 'ws://' + Context.cube_api_client.host + '/ws/lobbies/',
            token = Context.cube_api_client.token,
        )
        self.connected.emit(True)

    def get_lobbies(self) -> t.Mapping[str, Lobby]:
        if self._lobby_client is None:
            return {}
        return self._lobby_client.get_lobbies()

    def get_lobby(self, name: str) -> t.Optional[Lobby]:
        if self._lobby_client is None:
            return None
        return self._lobby_client.get_lobby(name)

    def create_lobby(
        self,
        name: str,
        game_type: str,
        lobby_options: LobbyOptions,
        game_options: t.Mapping[str, t.Any],
    ) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.create_lobby(name, game_type, lobby_options, game_options)

    def set_options(self, name: str, options: t.Mapping[str, t.Any]) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_options(name, options)

    def set_game_type(self, name: str, game_type: str, options: t.Mapping[str, t.Any]) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_game_type(name, game_type, options)

    def leave_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.leave_lobby(name)

    def join_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.join_lobby(name)

    def set_ready(self, name: str, ready: bool) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_ready(name, ready)

    def start_game(self, name: str) -> None:
        if self._lobby_client is None:
            return

        lobby = self._lobby_client.get_lobby(name)

        if lobby is None:
            return

        self._lobby_client.start_game(name)

        GameTypeOptions.save_options(lobby.game_type, lobby.game_options)
