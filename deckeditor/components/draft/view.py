from __future__ import annotations

import typing
import typing as t
from abc import abstractmethod

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QUndoStack

from frozendict import frozendict
from bidict import bidict

from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.grid import GridAligner
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.models.deck import PoolModel
from draft.client import DraftClient
from draft.models import Booster

from lobbyclient.client import LobbyClient, Lobby
from mtgorp.db.database import CardDatabase


class _DraftClient(DraftClient):

    def __init__(self, host: str, draft_id: str, db: CardDatabase, draft_model: DraftModel):
        super().__init__(host, draft_id, db)
        self._draft_model = draft_model

    def _received_booster(self, booster: Booster):
        print('received booster', booster)


class DraftModel(QObject):
    connected = pyqtSignal(bool)

    def __init__(self, key: str) -> None:
        super().__init__()

        self._key = key
        # self._name = name
        self._draft_client = _DraftClient(
            host = Context.cube_api_client.host if Context.cube_api_client else Context.host,
            draft_id = key,
            db = Context.db,
            draft_model = self,
        )

    @property
    def key(self) -> str:
        return self._key

    # @property
    # def name(self) -> str:
    #     return self._name

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


class DraftView(Editable):

    def __init__(
        self,
        draft_model: DraftModel,
    ) -> None:
        super().__init__()
        self._draft_model = draft_model

        self._undo_stack = Context.get_undo_stack()

        self._booster_view = CubeView(
            scene = CubeScene(GridAligner),
            undo_stack = self._undo_stack,
        )

        self._pool_model = PoolModel()

        self._pool_view = PoolView(
            self._pool_model
        )

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        layout = QtWidgets.QVBoxLayout(self)

        splitter.addWidget(self._booster_view)
        splitter.addWidget(self._pool_view)

        layout.addWidget(splitter)

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    def is_empty(self) -> bool:
        return super().is_empty()

    def persist(self) -> t.Any:
        return super().persist()

    @classmethod
    def load(cls, state: t.Any) -> Editable:
        return super().load(state)


# class DraftTabs(QtWidgets.QTabWidget):
#
#     def __init__(self, parent: t.Optional[QObject] = None):
#         super().__init__(parent)
#
#         # self.setTabsClosable(True)
#         # self.tabCloseRequested.connect(self._tab_close_requested)
#         #
#         # self._lobby_view.lobby_model.changed.connect(self._update_content)
#
#         self._drafts_map: t.MutableMapping[str, DraftModel] = {}
#
#         Context.draft_started.connect(self.add_draft)
#
#         # self.currentChanged.connect(self._current_changed)
#
#     def add_draft(self, draft_model: DraftModel) -> None:
#         if not draft_model.key in self._drafts_map:
#             self.addTab(
#                 DraftView(draft_model),
#                 draft_model.name,
#             )
#
#     def _tab_close_requested(self, index: int) -> None:
#         print('close tab at index', index)
#         # self._lobby_view.lobby_model.leave_lobby(
#         #     self._tabs_map.inverse[index]
#         # )
