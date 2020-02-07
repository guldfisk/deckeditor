from __future__ import annotations

import itertools
import typing as t
from collections import defaultdict

from PyQt5.QtCore import QPoint, pyqtSignal
from PyQt5.QtWidgets import QUndoCommand

from deckeditor.models.cubes.scenecard import SceneCard
from magiccube.collections import cubeable as Cubeable
from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.models.cubes.selection import SelectionScene
from deckeditor import values
from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.aligner import AlignmentPickUp, AlignmentDrop, Aligner, AlignmentMultiDrop
from mtgorp.models.persistent.printing import Printing


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

        if not (add_cards or remove_cards):
            self.setObsolete(True)
            return

        self._scene = scene
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


class CubeScene(SelectionScene):
    aligner_changed = pyqtSignal(Aligner)
    content_changed = pyqtSignal()

    def __init__(
        self,
        aligner_type: t.Optional[t.Type[Aligner]] = None,
        cards: t.Optional[t.Sequence[SceneCard]] = None,
        width: float = values.IMAGE_WIDTH * 12,
        height: float = values.IMAGE_HEIGHT * 8,
        mode: CubeEditMode = CubeEditMode.OPEN,
    ):
        super().__init__()
        self._mode = mode

        self.setSceneRect(
            0,
            0,
            width,
            height,
        )

        self._aligner = None if aligner_type is None else aligner_type(self)
        self._item_map: t.MutableMapping[Cubeable, t.List[SceneCard]] = defaultdict(list)
        self._related_scenes: t.AbstractSet[CubeScene] = {self}

        if cards is not None and self._aligner is not None:
            self.add_physical_cards(*cards)
            self._aligner.drop(
                cards,
                QPoint(),
            ).redo()

        self.aligner_changed.connect(self._on_aligner_changed)

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

    def _on_aligner_changed(self, aligner: Aligner) -> None:
        self._aligner = aligner

    def get_set_aligner(self, aligner_type: t.Type[Aligner]):
        new_aligner = aligner_type(self)
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
        width: float,
        height: float,
    ) -> CubeScene:
        cube_scene = CubeScene(
            width = width,
            height = height,
            mode = mode,
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
                self.width(),
                self.height(),
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

            removed_physical_cards = list(
                itertools.chain.from_iterable(
                    self._item_map.get(cubeable, [])[:-multiplicity]
                    for cubeable, multiplicity in
                    modification.removed_cubeables
                )
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
                        and isinstance(card, Printing)
                        and card.cubeable.cardboard in Context.basics
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

        # return CubeSceneModification(
        #     self,
        #     new_physical_cards,
        #     self._aligner.drop(new_physical_cards, QPoint() if position is None else position),
        #     self._aligner.pick_up(removed_physical_cards),
        #     removed_physical_cards,
        # )

    def add_physical_cards(self, *physical_cards: SceneCard) -> None:
        for card in physical_cards:
            self._item_map[card.cubeable].append(card)
            self.addItem(card)

        self.content_changed.emit()

    def remove_physical_cards(self, *physical_cards: SceneCard) -> None:
        for card in physical_cards:
            self._item_map[card.cubeable].remove(card)
            self.removeItem(card)

        self.content_changed.emit()
