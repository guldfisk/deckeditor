from __future__ import annotations

import pickle
import typing as t
from abc import abstractmethod

from magiccube.collections.cube import Cube
from magiccube.collections.infinites import Infinites
from mtgorp.models.collections.deck import Deck as OrpDeck
from mtgorp.models.serilization.serializeable import (
    Inflator,
    Serializeable,
    serialization_model,
)
from mtgorp.models.serilization.strategies.raw import RawStrategy
from PyQt5.QtCore import QObject, pyqtSignal

from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.context.context import Context
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.cubes.scenetypes import SceneType


class TabModel(Serializeable):
    @abstractmethod
    def serialize(self) -> serialization_model:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Serializeable:
        pass

    @abstractmethod
    def __hash__(self) -> int:
        pass

    @abstractmethod
    def __eq__(self, other: object) -> bool:
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
            "maindeck": self._maindeck.serialize(),
            "sideboard": self._sideboard.serialize(),
        }

    @classmethod
    def deserialize(cls, value: serialization_model, inflator: Inflator) -> Deck:
        return cls(
            maindeck=Cube.deserialize(value["maindeck"], inflator),
            sideboard=Cube.deserialize(value["sideboard"], inflator),
        )

    def as_primitive_deck(self) -> OrpDeck:
        return OrpDeck(
            self._maindeck.printings,
            self._sideboard.printings,
        )

    @classmethod
    def from_primitive_deck(cls, deck: OrpDeck) -> Deck:
        return cls(
            Cube(deck.maindeck),
            Cube(deck.sideboard),
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
        *,
        mode: CubeEditMode = CubeEditMode.OPEN,
    ):
        super().__init__()
        self._maindeck = (
            CubeScene(
                cards=maindeck if isinstance(maindeck, t.Sequence) else None,
                scene_type=SceneType.MAINDECK,
                mode=mode,
            )
            if maindeck is None or isinstance(maindeck, t.Sequence)
            else maindeck
        )
        self._sideboard = (
            CubeScene(
                cards=sideboard if isinstance(sideboard, t.Sequence) else None,
                scene_type=SceneType.SIDEBOARD,
                mode=mode,
            )
            if sideboard is None or isinstance(sideboard, t.Sequence)
            else sideboard
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

    def serialize(self) -> t.Mapping[str, t.Any]:
        return {
            "maindeck": self._maindeck,
            "sideboard": self._sideboard,
        }

    def persist(self) -> t.Any:
        return pickle.dumps(self.serialize())

    @classmethod
    def load(cls, state: t.Any) -> DeckModel:
        state = pickle.loads(state)
        return cls(
            state["maindeck"],
            state["sideboard"],
        )


class PoolModel(DeckModel):
    _default_infinite_names = (
        "Plains",
        "Island",
        "Swamp",
        "Forest",
        "Mountain",
    )

    def __init__(
        self,
        pool: t.Union[CubeScene, t.Sequence[PhysicalCard], None] = None,
        maindeck: t.Union[CubeScene, t.Sequence[PhysicalCard], None] = None,
        sideboard: t.Union[CubeScene, t.Sequence[PhysicalCard], None] = None,
        infinites: t.Optional[Infinites] = None,
    ):
        super().__init__(
            CubeScene(
                cards=maindeck if isinstance(maindeck, t.Sequence) else None,
                mode=CubeEditMode.CLOSED,
                scene_type=SceneType.MAINDECK,
            )
            if maindeck is None or isinstance(maindeck, t.Sequence)
            else maindeck,
            CubeScene(
                cards=sideboard if isinstance(sideboard, t.Sequence) else None,
                mode=CubeEditMode.CLOSED,
                scene_type=SceneType.SIDEBOARD,
            )
            if sideboard is None or isinstance(sideboard, t.Sequence)
            else sideboard,
        )
        self._pool = (
            CubeScene(
                cards=pool if isinstance(pool, t.Sequence) else None,
                mode=CubeEditMode.CLOSED,
                scene_type=SceneType.POOL,
            )
            if pool is None or isinstance(pool, t.Sequence)
            else pool
        )
        self._infinites = (
            Infinites(Context.db.cardboards[cardboard_name] for cardboard_name in self._default_infinite_names)
            if infinites is None
            else infinites
        )

        self._scenes = {self._maindeck, self._sideboard, self._pool}

        for scene in self._scenes:
            scene.related_scenes = self._scenes
            scene.infinites = self._infinites

        self._pool.changed.connect(self.changed)

    @property
    def pool(self) -> CubeScene:
        return self._pool

    @property
    def infinites(self) -> Infinites:
        return self._infinites

    @infinites.setter
    def infinites(self, value: Infinites) -> None:
        self._infinites = value
        for scene in self._scenes:
            scene.infinites = self._infinites

    def as_pool(self) -> Pool:
        return Pool(self._maindeck.cube + self._sideboard.cube + self._pool.cube)

    def serialize(self) -> t.Mapping[str, t.Any]:
        return {
            "pool": self._pool,
            "infinites": RawStrategy.serialize(self.infinites),
            **super().serialize(),
        }

    @classmethod
    def load(cls, state: t.Any) -> PoolModel:
        state = pickle.loads(state)
        return cls(
            maindeck=state["maindeck"],
            sideboard=state["sideboard"],
            pool=state["pool"],
            infinites=RawStrategy(Context.db).deserialize(Infinites, state["infinites"]),
        )
