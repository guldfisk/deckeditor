from __future__ import annotations

import typing as t

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from lobbyclient.client import Lobby

from deckeditor.components.lobbies.client import LobbyModelClientConnection


class LobbyViewInterface(QWidget):
    options_changed: pyqtSignal(dict)

    @property
    def lobby(self) -> t.Optional[Lobby]:
        raise NotImplemented()

    @property
    def lobby_model(self) -> LobbyModelClientConnection:
        raise NotImplemented()


class LobbiesViewInterface(QWidget):
    lobbies_changed = pyqtSignal()

    @property
    def lobby_model(self) -> LobbyModelClientConnection:
        raise NotImplemented()

    def set_model(self, lobby_model: LobbyModelClientConnection) -> None:
        raise NotImplemented()
