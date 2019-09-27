from __future__ import annotations

import typing as t

from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt, QObject, pyqtSignal

from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation
from mtgorp.models.collections.deck import Deck


class CubeModel(QObject):

    changed = pyqtSignal()

    def __init__(self, cube: t.Optional[Cube]) -> None:
        super().__init__()
        self._cube = Cube() if cube is None else cube

    @property
    def cube(self) -> Cube:
        return self._cube

    def modify(self, cube_delta_operation: CubeDeltaOperation) -> None:
        self._cube += cube_delta_operation
        self.changed.emit()


class DeckModel(QObject):

    changed = pyqtSignal()

    def __init__(self, maindeck: CubeModel, sideboard: CubeModel):
        super().__init__()
        self._maindeck = maindeck
        self._sideboard = sideboard

        self._maindeck.changed.connect(self.changed)
        self._sideboard.changed.connect(self.changed)

    @property
    def maindeck(self) -> CubeModel:
        return self._maindeck

    @property
    def sideboard(self) -> CubeModel:
        return self._sideboard