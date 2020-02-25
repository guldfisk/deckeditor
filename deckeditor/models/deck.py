from __future__ import annotations

import typing as t

from PyQt5.QtCore import QObject, pyqtSignal

from deckeditor.models.cubes.alignment.dynamicstackinggrid import DynamicStackingGrid
from mtgorp.models.serilization.serializeable import Serializeable, serialization_model, Inflator
from mtgorp.models.collections.deck import Deck as OrpDeck

from magiccube.collections.cube import Cube

from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.values import IMAGE_WIDTH, IMAGE_HEIGHT
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

    def as_primitive_deck(self) -> OrpDeck:
        return OrpDeck(
            self._maindeck.printings,
            self._sideboard.printings,
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


class DeckModel(QObject):
    changed = pyqtSignal()

    def __init__(
        self,
        maindeck: t.Union[CubeScene, t.Sequence[PhysicalCard], None] = None,
        sideboard: t.Union[CubeScene, t.Sequence[PhysicalCard], None] = None,
    ):
        super().__init__()
        self._maindeck = (
            CubeScene(
                aligner_type = DynamicStackingGrid,
                cards = maindeck if isinstance(maindeck, t.Sequence) else None,
                width = IMAGE_WIDTH * 15.5,
                height = IMAGE_HEIGHT * 6.3,
            )
            if sideboard is None or isinstance(maindeck, t.Sequence) else
            maindeck
        )
        self._sideboard = (
            CubeScene(
                aligner_type = DynamicStackingGrid,
                cards = sideboard if isinstance(sideboard, t.Sequence) else None,
                width = IMAGE_WIDTH * 3.3,
                height = IMAGE_HEIGHT * 6.3,
            )
            if sideboard is None or isinstance(sideboard, t.Sequence) else
            sideboard
        )

        for scene in (self._maindeck, self._sideboard):
            scene.related_scenes = {self._maindeck, self._sideboard}

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
            'maindeck': self._maindeck,
            'sideboard': self._sideboard,
        }

    @classmethod
    def load(cls, state: t.Any) -> DeckModel:
        return cls(
            state['maindeck'],
            state['sideboard'],
        )


class PoolModel(DeckModel):

    def __init__(
        self,
        pool: t.Union[CubeScene, t.Sequence[PhysicalCard], None] = None,
        maindeck: t.Union[CubeScene, t.Sequence[PhysicalCard], None] = None,
        sideboard: t.Union[CubeScene, t.Sequence[PhysicalCard], None] = None,
    ):
        super().__init__(
            CubeScene(
                aligner_type = DynamicStackingGrid,
                cards = maindeck if isinstance(maindeck, t.Sequence) else None,
                width = IMAGE_WIDTH * 15.5,
                height = IMAGE_HEIGHT * 6.3,
                mode = CubeEditMode.CLOSED,
            )
            if sideboard is None or isinstance(maindeck, t.Sequence) else
            maindeck,
            CubeScene(
                aligner_type = DynamicStackingGrid,
                cards = sideboard if isinstance(sideboard, t.Sequence) else None,
                width = IMAGE_WIDTH * 3.3,
                height = IMAGE_HEIGHT * 6.3,
                mode = CubeEditMode.CLOSED,
            )
            if sideboard is None or isinstance(sideboard, t.Sequence) else
            sideboard,
        )
        self._pool = (
            CubeScene(
                aligner_type = DynamicStackingGrid,
                cards = pool if isinstance(pool, t.Sequence) else None,
                width = IMAGE_WIDTH * 20.7,
                height = IMAGE_HEIGHT * 6.3,
                mode = CubeEditMode.CLOSED,
            )
            if sideboard is None or isinstance(pool, t.Sequence) else
            pool
        )

        scenes = {self._maindeck, self._sideboard, self._pool}

        for scene in scenes:
            scene.related_scenes = scenes

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
            'pool': self._pool,
            **super().persist(),
        }

    @classmethod
    def load(cls, state: t.Any) -> PoolModel:
        return cls(
            maindeck = state['maindeck'],
            sideboard = state['sideboard'],
            pool = state['pool'],
        )
