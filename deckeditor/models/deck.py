from __future__ import annotations

import typing as t

from PyQt5.QtCore import QObject, pyqtSignal

from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.models.cubes.cubescene import CubeScene
from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation


# class CubeModel(QObject):
#
#     changed = pyqtSignal(CubeDeltaOperation)
#
#     def __init__(self, cube: t.Optional[Cube] = None) -> None:
#         super().__init__()
#         self._cube = Cube() if cube is None else cube
#
#     @property
#     def cube(self) -> Cube:
#         return self._cube
#
#     def modify(self, cube_delta_operation: CubeDeltaOperation) -> None:
#         self._cube += cube_delta_operation
#         self.changed.emit(cube_delta_operation)


class DeckModel(QObject):

    changed = pyqtSignal()

    def __init__(self, maindeck: t.Optional[CubeScene] = None, sideboard: t.Optional[CubeScene] = None):
        super().__init__()
        self._maindeck = CubeScene(StaticStackingGrid) if maindeck is None else maindeck
        self._sideboard = CubeScene(StaticStackingGrid) if sideboard is None else sideboard

        self._maindeck.changed.connect(self.changed)
        self._sideboard.changed.connect(self.changed)

    @property
    def maindeck(self) -> CubeScene:
        return self._maindeck

    @property
    def sideboard(self) -> CubeScene:
        return self._sideboard


class PoolModel(DeckModel):

    def __init__(self, pool: t.Optional[CubeScene] = None):
        super().__init__(None, None)
        self._pool = CubeScene(StaticStackingGrid) if pool is None else pool

        self._pool.changed.connect(self.changed)

    @property
    def pool(self) -> CubeScene:
        return self._pool
