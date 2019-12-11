from __future__ import annotations

import typing
import typing as t
from abc import abstractmethod

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem

from frozendict import frozendict
from bidict import bidict

from deckeditor.context.context import Context
from draft.client import DraftClient
from draft.models import Booster

from lobbyclient.client import LobbyClient, Lobby
from mtgorp.db.database import CardDatabase


class _DraftClient(DraftClient):

    def __init__(self, host: str, draft_id: str, db: CardDatabase, draft_model: DraftModel):
        super().__init__(host, draft_id, db)
        self._draft_model = draft_model

    def _received_booster(self, booster: Booster):
        pass


class DraftModel(QObject):
    connected = pyqtSignal(bool)

    def __init__(self, key: str, name: str, parent: t.Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._key = key
        self._name = name
        self._draft_client = _DraftClient(
            host = Context.host,
            draft_id = key,
            db = Context.db,
            draft_model = self,
        )

    @property
    def key(self) -> str:
        return self._key

    @property
    def name(self) -> str:
        return self._name

    def _logged_in(self, _):
        pass
        # if self._lobby_client is not None:
        #     self._lobby_client.close()
        # self._lobby_client = _LobbyClient(
        #     self,
        #     url = 'ws://' + Context.host + '/ws/lobbies/',
        #     token = Context.token,
        # )
        # self.connected.emit(True)


class DraftView(QtWidgets.QWidget):

    def __init__(self, draft_model: DraftModel, parent: t.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._draft_model = draft_model



class DraftTabs(QtWidgets.QTabWidget):

    def __init__(self, parent: t.Optional[QObject] = None):
        super().__init__(parent)

        # self.setTabsClosable(True)
        # self.tabCloseRequested.connect(self._tab_close_requested)
        #
        # self._lobby_view.lobby_model.changed.connect(self._update_content)

        self._drafts_map: t.MutableMapping[str, DraftModel] = {}

        Context.draft_started.connect(self.add_draft)

        # self.currentChanged.connect(self._current_changed)

    def add_draft(self, draft_model: DraftModel) -> None:
        if not draft_model.key in self._drafts_map:
            self.addTab(
                DraftView(draft_model),
                draft_model.name,
            )

    def _tab_close_requested(self, index: int) -> None:
        self._lobby_view.lobby_model.leave_lobby(
            self._tabs_map.inverse[index]
        )
