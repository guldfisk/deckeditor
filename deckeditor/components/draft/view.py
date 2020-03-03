from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QUndoStack

from mtgorp.db.database import CardDatabase

from magiccube.collections.cubeable import Cubeable

from cubeclient.models import ApiClient

from mtgdraft.client import DraftClient
from mtgdraft.models import Booster, DraftRound

from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.grid import GridAligner
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.deck import PoolModel


class _DraftClient(DraftClient):

    def __init__(self, api_client: ApiClient, draft_id: str, db: CardDatabase, draft_model: DraftModel):
        super().__init__(api_client, draft_id, db)
        self._draft_model = draft_model

    def _received_booster(self, booster: Booster) -> None:
        self._draft_model.received_booster.emit(booster)

    def _picked(self, pick: Cubeable) -> None:
        self._draft_model.cubeable_picked.emit(pick)

    def _completed(self) -> None:
        pass

    def _on_start(self) -> None:
        self._draft_model.draft_started.emit()

    def _on_round(self, draft_round: DraftRound) -> None:
        self._draft_model.round_started.emit(draft_round)


class DraftModel(QObject):
    connected = pyqtSignal(bool)
    received_booster = pyqtSignal(Booster)
    cubeable_picked = pyqtSignal(object)
    draft_started = pyqtSignal()
    round_started = pyqtSignal(DraftRound)

    def __init__(self, key: str) -> None:
        super().__init__()

        self._key = key
        self._draft_client: t.Optional[DraftClient] = None

    def connect(self) -> None:
        self._draft_client = _DraftClient(
            api_client = Context.cube_api_client,
            draft_id = self._key,
            db = Context.db,
            draft_model = self,
        )

    def close(self) -> None:
        if self._draft_client:
            self._draft_client.close()

    @property
    def draft_client(self) -> t.Optional[DraftClient]:
        return self._draft_client

    @property
    def key(self) -> str:
        return self._key

    def pick(self, cubeable: Cubeable) -> None:
        self._draft_client.pick(cubeable)


# class DraftInfo(QtWidgets.QWidget):
#
#     def __init__(self):
#         super().__init__()
#
#         self._players_list
#
#         layout = QtWidgets.QVBoxLayout()


class BoosterView(QtWidgets.QWidget):

    def __init__(self, draft_model: DraftModel):
        super().__init__()
        self._undo_stack = Context.get_undo_stack()

        self._draft_model = draft_model

        self._players_list = QtWidgets.QLabel()
        self._booster_scene = CubeScene(GridAligner)
        self._booster_view = CubeView(
            scene = self._booster_scene,
            undo_stack = self._undo_stack,
        )

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._players_list, QtCore.Qt.AlignTop)
        layout.addWidget(self._booster_view)

        self._draft_model.received_booster.connect(self._on_receive_booster)
        self._draft_model.cubeable_picked.connect(self._on_cubeable_picked)
        self._draft_model.round_started.connect(self._on_round_started)
        self._booster_view.cubeable_double_clicked.connect(self._draft_model.pick)

    def _on_round_started(self, draft_round: DraftRound) -> None:
        self._players_list.setText(
            'Draft order: ' + (
                ' -> '
                if draft_round.clockwise else
                ' <- '
            ).join(
                drafter.username
                for drafter in
                self._draft_model.draft_client.drafters
            )
        )

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
        self._booster_scene.get_cube_modification(
            remove = self._booster_scene.items(),
        ).redo()


class DraftView(Editable):

    def __init__(
        self,
        draft_model: DraftModel,
    ) -> None:
        super().__init__()
        self._draft_model = draft_model

        self._undo_stack = Context.get_undo_stack()

        self._booster_view = BoosterView(draft_model)

        self._pool_model = PoolModel()

        self._pool_view = PoolView(
            self._pool_model
        )

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        layout = QtWidgets.QVBoxLayout(self)

        splitter.addWidget(self._booster_view)
        splitter.addWidget(self._pool_view)

        layout.addWidget(splitter)

        self._draft_model.connect()

    def close(self) -> None:
        self._draft_model.close()

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

