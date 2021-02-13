from __future__ import annotations

import itertools
import typing as t
from collections import defaultdict
from dataclasses import dataclass

from frozendict import frozendict

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QPoint, pyqtSignal
from PyQt5.QtWidgets import QUndoCommand

from yeetlong.counters import Counter

from mtgorp.models.interfaces import Printing

from magiccube.collections.cubeable import Cubeable
from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation
from magiccube.collections.infinites import Infinites

from deckeditor.components.settings import settings
from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.models.cubes.alignment.aligner import AlignmentPickUp, AlignmentDrop, Aligner, AlignmentMultiDrop
from deckeditor.models.cubes.alignment.aligners import get_default_aligner_type
from deckeditor.models.cubes.scenecard import SceneCard
from deckeditor.models.cubes.scenetypes import SceneType
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.sorting.sorting import SortProperty, SortMacro, SortSpecification, CMCExtractor
from deckeditor.store import EDB, models


class IntraCubeSceneMove(QUndoCommand):

    def __init__(self, pick_up: AlignmentPickUp, drop: AlignmentDrop):
        self._pick_up = pick_up
        self._drop = drop
        super().__init__(
            str(self)
        )

    def __str__(self) -> str:
        return 'intra scene move'

    def redo(self) -> None:
        self._pick_up.redo()
        self._drop.redo()

    def undo(self) -> None:
        self._drop.undo()
        self._pick_up.undo()


class InterCubeSceneMove(QUndoCommand):

    def __init__(
        self,
        cards: t.Iterable[SceneCard],
        from_scene: CubeScene,
        pick_up: AlignmentPickUp,
        to_scene: CubeScene,
        drop: AlignmentDrop,
    ):
        self._cards = list(cards)
        self._from_scene = from_scene
        self._pick_up = pick_up
        self._to_scene = to_scene
        self._drop = drop

        super().__init__('Inter scene move')

    def redo(self) -> None:
        self._pick_up.redo()
        self._from_scene.remove_physical_cards(*self._cards)
        self._to_scene.add_physical_cards(*self._cards)
        self._drop.redo()

    def undo(self) -> None:
        self._drop.undo()
        self._to_scene.remove_physical_cards(*self._cards)
        self._from_scene.add_physical_cards(*self._cards)
        self._pick_up.undo()


class CubeSceneModification(QUndoCommand):

    def __init__(
        self,
        scene: CubeScene,
        add_cards: t.Sequence[SceneCard],
        remove_cards: t.Sequence[SceneCard],
        point: QPoint,
    ):
        super().__init__('Cube modification')
        self._scene = scene

        if not (add_cards or remove_cards):
            self.setObsolete(True)
            return

        self._add = add_cards
        self._pick_up = self._scene.aligner.pick_up(remove_cards)
        self._drop = self._scene.aligner.drop(add_cards, point)
        self._remove = remove_cards

    def redo(self) -> None:
        self._scene.add_physical_cards(*self._add)
        self._drop.redo()
        self._pick_up.redo()
        self._scene.remove_physical_cards(*self._remove)

    def undo(self) -> None:
        self._scene.add_physical_cards(*self._remove)
        self._pick_up.undo()
        self._drop.undo()
        self._scene.remove_physical_cards(*self._add)


class ChangeAligner(QUndoCommand):

    def __init__(
        self,
        scene: CubeScene,
        pick_up: AlignmentPickUp,
        from_aligner: Aligner,
        to_aligner: Aligner,
        multi_drops: AlignmentMultiDrop
    ):
        self._scene = scene
        self._pick_up = pick_up
        self._from_aligner = from_aligner
        self._to_aligner = to_aligner
        self._multi_drops = multi_drops
        super().__init__('Change aligner')

    def redo(self) -> None:
        self._pick_up.redo()
        self._scene.aligner_changed.emit(self._to_aligner)
        self._multi_drops.redo()

    def undo(self) -> None:
        self._multi_drops.undo()
        self._scene.aligner_changed.emit(self._from_aligner)
        self._pick_up.undo()


@dataclass
class PhysicalCardChange(object):
    added: t.Collection[SceneCard] = ()
    removed: t.Collection[SceneCard] = ()

    @property
    def cube_delta_operation(self):
        return CubeDeltaOperation(
            Counter(
                card.cubeable for card in self.added
            ) - Counter(
                card.cubeable for card in self.removed
            )
        )


DEFAULT_ALIGNER_MARKER = object()


class CubeScene(SelectionScene):
    aligner_changed = pyqtSignal(Aligner)
    content_changed = pyqtSignal(PhysicalCardChange)

    items: t.Callable[[], t.Sequence[SceneCard]]
    selectedItems: t.Callable[[], t.Sequence[SceneCard]]

    def __init__(
        self,
        aligner_type: t.Union[t.Type[Aligner], None, DEFAULT_ALIGNER_MARKER] = DEFAULT_ALIGNER_MARKER,
        aligner_options: t.Mapping[str, t.Any] = frozendict(),
        cards: t.Optional[t.Sequence[SceneCard]] = None,
        mode: CubeEditMode = CubeEditMode.OPEN,
        scene_type: SceneType = SceneType.MAINDECK,
        infinites: Infinites = Infinites(),
    ):
        super().__init__()

        self.setSceneRect(
            QtCore.QRectF(
                0,
                0,
                1e10,
                1e10,
            )
        )

        self._mode = mode
        self._scene_type = scene_type

        self.infinites = infinites

        if aligner_type == DEFAULT_ALIGNER_MARKER:
            aligner_type = get_default_aligner_type(self._scene_type)

        if aligner_type is None:
            self._aligner = None
        else:
            options = dict(
                aligner_type.schema.deserialize_raw(
                    settings.SCENE_DEFAULTS.get_value()[self._scene_type.value]['aligner_options']
                )
            )
            options.update(aligner_options)
            self._aligner = aligner_type(
                self,
                **options,
            )

        self._item_map: t.MutableMapping[Cubeable, t.List[SceneCard]] = defaultdict(list)
        self._related_scenes: t.AbstractSet[CubeScene] = {self}

        if cards is not None and self._aligner is not None:
            self.add_physical_cards(*cards)
            self._aligner.drop(cards, QPoint()).redo()

        self._last_horizontal_sort: t.Optional[t.Type[SortProperty]] = None
        self._last_vertical_sort: t.Optional[t.Type[SortProperty]] = None
        self._auto_sort = False

        self.aligner_changed.connect(self._on_aligner_changed)

    @property
    def scene_type(self) -> SceneType:
        return self._scene_type

    @property
    def cube(self) -> Cube:
        return Cube(
            item.cubeable
            for item in
            self.items()
            if isinstance(item, SceneCard)
        )

    @property
    def aligner(self) -> Aligner:
        return self._aligner

    @property
    def related_scenes(self) -> t.AbstractSet[CubeScene]:
        return self._related_scenes

    @related_scenes.setter
    def related_scenes(self, scenes: t.AbstractSet[CubeScene]) -> None:
        self._related_scenes = scenes

    @property
    def auto_sort(self) -> bool:
        return self._auto_sort

    def _on_aligner_changed(self, aligner: Aligner) -> None:
        self._aligner = aligner

    def get_set_aligner(self, aligner_type: t.Type[Aligner]) -> ChangeAligner:
        new_aligner = aligner_type(self, **aligner_type.schema.deserialize_raw(self._aligner.options))
        return ChangeAligner(
            self,
            self._aligner.pick_up(
                self.items()
            ),
            self._aligner,
            new_aligner,
            new_aligner.multi_drop(
                [
                    ((card,), card.pos())
                    for card in
                    self.items()
                ]
            ),
        )

    @classmethod
    def _load(
        cls,
        aligner: Aligner,
        mode: CubeEditMode,
        name: SceneType,
    ) -> CubeScene:
        cube_scene = CubeScene(
            aligner_type = None,
            mode = mode,
            scene_type = name,
        )
        aligner._scene = cube_scene
        cube_scene._aligner = aligner
        cube_scene.add_physical_cards(*aligner.cards)
        aligner.realign()
        return cube_scene

    def __reduce__(self):
        return (
            self._load,
            (
                self._aligner,
                self._mode,
                self._scene_type,
            ),
            {'_related_scenes': self._related_scenes},
        )

    def get_intra_move(self, items: t.Sequence[SceneCard], position: QPoint) -> IntraCubeSceneMove:
        return IntraCubeSceneMove(
            self._aligner.pick_up(items),
            self._aligner.drop(items, position),
        )

    def get_inter_move(
        self,
        cards: t.Sequence[SceneCard],
        target_scene: CubeScene,
        position: QPoint,
    ) -> InterCubeSceneMove:
        return InterCubeSceneMove(
            cards,
            self,
            self._aligner.pick_up(cards),
            target_scene,
            target_scene._aligner.drop(cards, position),
        )

    def get_cube_modification(
        self,
        modification: t.Optional[CubeDeltaOperation] = None,
        add: t.Optional[t.Sequence[SceneCard]] = None,
        remove: t.Optional[t.Sequence[SceneCard]] = None,
        position: t.Optional[QPoint] = None,
        closed_operation: bool = False,
    ) -> CubeSceneModification:
        if isinstance(modification, CubeDeltaOperation):
            new_physical_cards = list(
                itertools.chain.from_iterable(
                    (SceneCard.from_cubeable(cubeable) for _ in range(multiplicity))
                    for cubeable, multiplicity in
                    modification.new_cubeables
                )
            )

            removed_physical_cards = self.get_cards_from_cubeables(
                (cubeable, -multiplicity)
                for cubeable, multiplicity in
                modification.removed_cubeables
            )

        else:
            new_physical_cards = add if add is not None else []
            removed_physical_cards = remove if remove is not None else []

        if not closed_operation and self._mode == CubeEditMode.CLOSED:
            new_physical_cards, removed_physical_cards = (
                [
                    card
                    for card in
                    cards
                    if (
                    isinstance(card, SceneCard)
                    and isinstance(card.cubeable, Printing)
                    and card.cubeable.cardboard in self.infinites
                )
                ]
                for cards in
                (new_physical_cards, removed_physical_cards)
            )

        return CubeSceneModification(
            self,
            new_physical_cards,
            removed_physical_cards,
            QPoint() if position is None else position,
        )

    def get_cards_from_cubeables(self, cubeables: t.Iterable[t.Tuple[Cubeable, int]]) -> t.Collection[SceneCard]:
        return list(
            itertools.chain.from_iterable(
                self._item_map[cubeable][:multiplicity]
                for cubeable, multiplicity in
                cubeables
            )
        )

    def add_physical_cards(self, *physical_cards: SceneCard) -> None:
        for card in physical_cards:
            self._item_map[card.cubeable].append(card)
            self.addItem(card)

        self.content_changed.emit(PhysicalCardChange(added = physical_cards))

    def remove_physical_cards(self, *physical_cards: SceneCard) -> None:
        for card in physical_cards:
            self._item_map[card.cubeable].remove(card)
            self.removeItem(card)

        self.content_changed.emit(PhysicalCardChange(removed = physical_cards))

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        if self._aligner:
            self._aligner.draw_background(painter, rect)

    def get_default_sort(self) -> QUndoCommand:
        return self.aligner.sort(
            sort_macro = EDB.Session.query(models.SortMacro).get(
                settings.SCENE_DEFAULTS.get_value()[self._scene_type.value]['sort_macro']
            ) or SortMacro(
                specifications = [
                    SortSpecification(
                        sort_property = CMCExtractor,
                    )
                ]
            ),
            cards = self.items(),
        )

    def __repr__(self):
        return '{}()'.format(
            self.__class__.__name__,
        )
