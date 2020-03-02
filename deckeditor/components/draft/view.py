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
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.deck import PoolModel
from draft.client import DraftClient
from draft.models import Booster

from lobbyclient.client import LobbyClient, Lobby
from magiccube.collections.cubeable import Cubeable
from mtgorp.db.database import CardDatabase


class _DraftClient(DraftClient):

    def __init__(
        self,
        host: str,
        draft_id: str,
        db: CardDatabase,
        draft_model: DraftModel,
    ):
        super().__init__(host, draft_id, db)
        self._draft_model = draft_model

    def _received_booster(self, booster: Booster):
        print('received booster', booster)
        self._draft_model.received_booster.emit(booster)

    def _picked(self, pick: Cubeable):
        print('picked in draft client')
        self._draft_model.cubeable_picked.emit(pick)


class DraftModel(QObject):
    connected = pyqtSignal(bool)
    received_booster = pyqtSignal(Booster)
    cubeable_picked = pyqtSignal(object)

    def __init__(self, key: str) -> None:
        super().__init__()

        self._key = key
        # self._name = name
        self._draft_client: t.Optional[DraftClient] = None

    def connect(self) -> None:
        self._draft_client = _DraftClient(
            host = Context.cube_api_client.host if Context.cube_api_client else Context.host,
            draft_id = self._key,
            db = Context.db,
            draft_model = self,
        )

    @property
    def key(self) -> str:
        return self._key

    def pick(self, cubeable: Cubeable) -> None:
        self._draft_client.pick(cubeable)

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
    # received_booster = pyqtSignal(Booster)

    def __init__(
        self,
        draft_model: DraftModel,
    ) -> None:
        super().__init__()
        self._draft_model = draft_model

        self._undo_stack = Context.get_undo_stack()

        self._booster_scene = CubeScene(GridAligner)

        self._booster_view = CubeView(
            scene = self._booster_scene,
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

        self._draft_model.received_booster.connect(self._on_receive_booster)
        self._draft_model.cubeable_picked.connect(self._on_cubeable_picked)
        self._booster_view.cube_image_view.card_double_clicked.connect(self._on_booster_card_double_clicked)

        self._draft_model.connect()

    def _on_receive_booster(self, booster: Booster) -> None:
        self._booster_scene.get_cube_modification(
            add = list(
                map(
                    PhysicalCard.from_cubeable,
                    booster.cubeables,
                )
            ),
            remove = self._booster_scene.items(),
        ).redo()

    def _on_cubeable_picked(self, cubeable: Cubeable) -> None:
        print('on cubeable picked in ')
        self._booster_scene.get_cube_modification(
            remove = self._booster_scene.items(),
        ).redo()

    def _on_booster_card_double_clicked(self, card: PhysicalCard) -> None:
        self._draft_model.pick(card.cubeable)

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
