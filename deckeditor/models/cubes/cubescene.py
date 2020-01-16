from __future__ import annotations

import itertools
import typing as t
from collections import defaultdict

from PyQt5.QtCore import QPoint, pyqtSignal
from PyQt5.QtWidgets import QGraphicsItem, QUndoCommand

from deckeditor.models.cubes.alignment.aligner import AlignmentPickUp, AlignmentDrop, Aligner
from magiccube.collections import cubeable as Cubeable
from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor import values


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
            cards: t.Iterable[PhysicalCard],
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


class CubeSceneRemove(QUndoCommand):

    def __init__(self, scene: CubeScene, pick_up: AlignmentPickUp, cards: t.Iterable[PhysicalCard]):
        self._scene = scene
        self._pick_up = pick_up
        self._cards = list(cards)
        super().__init__('Remove cubeables')

    def redo(self) -> None:
        self._pick_up.redo()
        self._scene.remove_physical_cards(*self._cards)

    def undo(self) -> None:
        self._scene.add_physical_cards(*self._cards)
        self._pick_up.undo()


class CubeSceneModification(QUndoCommand):

    def __init__(
            self,
            scene: CubeScene,
            add: t.Iterable[PhysicalCard],
            drop: AlignmentDrop,
            pick_up: AlignmentPickUp,
            remove: t.Iterable[PhysicalCard],
    ):
        self._scene = scene
        self._add = add
        self._drop = drop
        self._pick_up = pick_up
        self._remove = remove
        super().__init__('Cube modification')

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
            drops: t.Sequence[AlignmentDrop],
    ):
        self._scene = scene
        self._pick_up = pick_up
        self._from_aligner = from_aligner
        self._to_aligner = to_aligner
        self._drops = drops
        super().__init__('Change aligner')

    def redo(self) -> None:
        self._pick_up.redo()
        self._scene.aligner_changed.emit(self._to_aligner)
        for drop in self._drops:
            drop.redo()

    def undo(self) -> None:
        for drop in reversed(self._drops):
            drop.undo()
        self._scene.aligner_changed.emit(self._from_aligner)
        self._pick_up.undo()


class CubeScene(SelectionScene):
    aligner_changed = pyqtSignal(Aligner)

    def __init__(self, aligner_type: t.Optional[t.Type[Aligner]], cube: t.Optional[Cube] = None):
        super().__init__()
        # self._cube_model = cube_model

        self.setSceneRect(0, 0, values.IMAGE_WIDTH * 12, values.IMAGE_HEIGHT * 8)

        self._aligner = aligner_type(self)

        self._item_map: t.MutableMapping[Cubeable, t.List[PhysicalCard]] = defaultdict(list)

        if cube is not None:
            for cubeable in cube:
                self.add_cubeables(cubeable)
            self._aligner.drop(
                self.items(),
                QPoint(),
            ).redo()

        self.aligner_changed.connect(self._on_aligner_changed)

    # @property
    # def cube_model(self) -> CubeModel:
    #     return self._cube_model

    @property
    def cube(self) -> Cube:
        return Cube(
            item.cubeable
            for item in
            self.items()
            if isinstance(item, PhysicalCard)
        )

    @property
    def aligner(self) -> Aligner:
        return self._aligner

    def _on_aligner_changed(self, aligner: Aligner) -> None:
        self._aligner = aligner

    # @aligner.setter
    # def aligner(self, value: Aligner) -> None:
    #     self._aligner = value

    def get_set_aligner(self, aligner_type: t.Type[Aligner]):
        new_aligner = aligner_type(self)
        return ChangeAligner(
            self,
            self._aligner.pick_up(
                self.items()
            ),
            self._aligner,
            new_aligner,
            [new_aligner.drop((card,), card.pos()) for card in self.items()],
        )

    # def set_aligner(self, aligner_type: t.Type[Aligner]) -> None:
    #     cards = list(
    #         itertools.chain(
    #             *self._item_map.values()
    #         )
    #     )
    #     self._aligner.pick_up(cards).redo()
    #     self._aligner = aligner_type(self)
    #     for card in cards:
    #         self._aligner.drop((card,), card.pos()).redo()

    # def pick_up(self, items: t.Iterable[PhysicalCard]) -> None:
    #     if self._aligner is not None:
    #         self._aligner.pick_up(items)
    #
    # def drop(self, items: t.Iterable[PhysicalCard], position: QPoint) -> None:
    #     if self._aligner is not None:
    #         self._aligner.drop(items, position)

    def get_intra_move(self, items: t.Sequence[PhysicalCard], position: QPoint) -> IntraCubeSceneMove:
        return IntraCubeSceneMove(
            self._aligner.pick_up(items),
            self._aligner.drop(items, position),
        )

    def get_inter_move(
            self,
            cards: t.Sequence[PhysicalCard],
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
            delta_operation: CubeDeltaOperation,
            position: t.Optional[QPoint] = None,
    ) -> CubeSceneModification:
        new_physical_cards = list(
            itertools.chain.from_iterable(
                (PhysicalCard(cubeable) for _ in range(multiplicity))
                for cubeable, multiplicity in
                delta_operation.new_cubeables
            )
        )

        removed_physical_cards = list(
            itertools.chain.from_iterable(
                self._item_map.get(cubeable, [])[:-multiplicity]
                for cubeable, multiplicity in
                delta_operation.removed_cubeables
            )
        )

        return CubeSceneModification(
            self,
            new_physical_cards,
            self._aligner.drop(new_physical_cards, QPoint() if position is None else position),
            self._aligner.pick_up(removed_physical_cards),
            removed_physical_cards,
        )

    def get_cube_scene_remove(self, cards: t.Iterable[PhysicalCard]):
        cards = list(cards)
        return CubeSceneRemove(
            self,
            self._aligner.pick_up(cards),
            cards,
        )

    def add_physical_cards(self, *physical_cards: PhysicalCard) -> None:
        for card in physical_cards:
            self._item_map[card.cubeable].append(card)
            self.addItem(card)

    def remove_physical_cards(self, *physical_cards: PhysicalCard) -> None:
        for card in physical_cards:
            print('remote', card.cubeable)
            self._item_map[card.cubeable].remove(card)
            self.removeItem(card)

    def add_cubeables(self, *cubeables: Cubeable) -> None:
        for cubeable in cubeables:
            physical_card = PhysicalCard(cubeable)
            self._item_map[cubeable].append(physical_card)
            self.addItem(physical_card)

    def remove_cubeables(self, *cubeables: Cubeable) -> None:
        for cubeable in cubeables:
            physical_card = self._item_map[cubeable].pop()
            self.removeItem(physical_card)
    #
    # def _update(self, delta_operation: CubeDeltaOperation) -> None:
    #     for cubeable, multiplicity in delta_operation.removed_cubeables:
    #         for _ in range(-multiplicity):
    #             self.remove_cubeable(cubeable)
    #
    #     for cubeable, multiplicity in delta_operation.new_cubeables:
    #         for _ in range(multiplicity):
    #             self.add_cubeable(cubeable)
