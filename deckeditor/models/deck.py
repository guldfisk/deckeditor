from __future__ import annotations

import typing as t

from PyQt5.QtCore import QObject, pyqtSignal

from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.models.cubes.cubescene import CubeScene
from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation
from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator


class Deck(Serializeable):

    def __init__(self, maindeck: Cube, sideboard: Cube):
        self._maindeck = maindeck
        self._sideboard = sideboard

    @property
    def maindeck(self) -> Cube:
        return self._maindeck

    @property
    def sideboard(self) -> Cube:
        return self._sideboard

    def serialize(self) -> serialization_model:
        return {
            'maindeck': self._maindeck.serialize(),
            'sideboard': self._sideboard.serialize(),
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Serializeable:
        return cls(
            maindeck = Cube.deserialize(value['maindeck'], inflator),
            sideboard = Cube.deserialize(value['sideboard'], inflator),
        )

    def __hash__(self) -> int:
        return hash((self._maindeck, self._sideboard))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._maindeck == other._maindeck
            and self._sideboard == other._sideboard
        )


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

    def as_deck(self) -> Deck:
        return Deck(
            self._maindeck.cube,
            self._sideboard.cube,
        )

    def persist(self) -> t.Any:
        return {
            'maindeck': self._maindeck.persist(),
            'sideboard': self._sideboard.persist(),
        }

    @classmethod
    def load(cls, state: t.Any) -> DeckModel:
        return DeckModel(
            CubeScene.load(state['maindeck']),
            CubeScene.load(state['sideboard']),
        )


class PoolModel(DeckModel):

    def __init__(self, pool: t.Optional[CubeScene] = None):
        super().__init__(None, None)
        self._pool = CubeScene(StaticStackingGrid) if pool is None else pool

        self._pool.changed.connect(self.changed)

    @property
    def pool(self) -> CubeScene:
        return self._pool
