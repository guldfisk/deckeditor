from __future__ import annotations

import typing as t

from PyQt5.QtCore import QObject, pyqtSignal

from deckeditor.values import IMAGE_WIDTH, IMAGE_HEIGHT
from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator

from magiccube.collections.cube import Cube

from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.models.cubes.cubescene import CubeScene


class TabModel(Serializeable):
    pass


class Deck(TabModel):

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
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Deck:
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


class Pool(Cube, TabModel):
    pass
    # def __init__(self, maindeck: Cube, sideboard: Cube, pool: Cube):
    #     self._maindeck = maindeck
    #     self._sideboard = sideboard
    #     self._pool = pool
    #
    # @property
    # def maindeck(self) -> Cube:
    #     return self._maindeck
    #
    # @property
    # def sideboard(self) -> Cube:
    #     return self._sideboard
    #
    # @property
    # def pool(self) -> Cube:
    #     return self._pool
    #
    # def serialize(self) -> serialization_model:
    #     return {
    #         'maindeck': self._maindeck.serialize(),
    #         'sideboard': self._sideboard.serialize(),
    #         'pool': self._pool.serialize(),
    #     }
    #
    # @classmethod
    # def deserialize(cls, value: serialization_model, inflator: Inflator) -> Pool:
    #     return cls(
    #         maindeck = Cube.deserialize(value['maindeck'], inflator),
    #         sideboard = Cube.deserialize(value['sideboard'], inflator),
    #         pool = Cube.deserialize(value['pool'], inflator),
    #     )
    #
    # def __hash__(self) -> int:
    #     return hash((self._maindeck, self._sideboard, self._pool))
    #
    # def __eq__(self, other: object) -> bool:
    #     return (
    #         isinstance(other, self.__class__)
    #         and self._maindeck == other._maindeck
    #         and self._sideboard == other._sideboard
    #         and self._pool == other._pool
    #     )


class DeckModel(QObject):
    changed = pyqtSignal()

    def __init__(
        self,
        maindeck: t.Union[CubeScene, Cube, None] = None,
        sideboard: t.Union[CubeScene, Cube, None] = None,
    ):
        super().__init__()
        self._maindeck = (
            CubeScene(StaticStackingGrid)
            if maindeck is None else
            CubeScene(aligner_type = StaticStackingGrid, cube = maindeck)
            if isinstance(maindeck, Cube) else
            maindeck
        )
        self._sideboard = (
            CubeScene(
                aligner_type = StaticStackingGrid,
                cube = sideboard if isinstance(sideboard, Cube) else None,
                width = IMAGE_WIDTH * 3.3,
                height = IMAGE_HEIGHT * 5.5,
            )
            if sideboard is None or isinstance(sideboard, Cube) else
            sideboard
        )

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
        return cls(
            CubeScene.load(state['maindeck']),
            CubeScene.load(state['sideboard']),
        )


class PoolModel(DeckModel):

    def __init__(
        self,
        pool: t.Optional[CubeScene] = None,
        maindeck: t.Optional[CubeScene] = None,
        sideboard: t.Optional[CubeScene] = None,
    ):
        super().__init__(maindeck, sideboard)
        self._pool = CubeScene(StaticStackingGrid) if pool is None else pool

        self._pool.changed.connect(self.changed)

    @property
    def pool(self) -> CubeScene:
        return self._pool

    def as_pool(self) -> Pool:
        return Pool(
            self._maindeck.cube + self._sideboard.cube + self._pool.cube
        )

    def persist(self) -> t.Any:
        return {
            'pool': self._pool.persist(),
            **super().persist(),
        }

    @classmethod
    def load(cls, state: t.Any) -> PoolModel:
        return cls(
            maindeck = CubeScene.load(state['maindeck']),
            sideboard = CubeScene.load(state['sideboard']),
            pool = CubeScene.load(state['pool']),
        )
