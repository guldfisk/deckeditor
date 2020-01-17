from __future__ import annotations

import copy
import typing as t

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoCommand

from deckeditor.models.cubes.alignment.aligner import Aligner, AlignmentDrop
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.sorting.sort import SortProperty, extract_sort_value
from deckeditor.values import IMAGE_WIDTH, IMAGE_HEIGHT
from mtgimg.interface import SizeSlug

from deckeditor.garbage.cardcontainers.physicalcard import PhysicalCard


class GridDrop(AlignmentDrop):

    def __init__(self, aligner: GridAligner, cards: t.Iterable[PhysicalCard], idx: int):
        self._aligner = aligner
        self._cards = list(cards)
        self._idx = idx

    def redo(self):
        self._aligner.cards[self._idx:self._idx] = self._cards
        self._aligner.realign(self._idx)

    def undo(self):
        del self._aligner.cards[self._idx:self._idx + len(self._cards)]
        self._aligner.realign(self._idx)


class GridPickUp(AlignmentDrop):

    def __init__(self, aligner: GridAligner, cards: t.Iterable[PhysicalCard]):
        self._aligner = aligner
        self._cards = list(cards)

        self._indexes = sorted(
            (
                (card, self._aligner.cards.index(card))
                for card in
                self._cards
            ),
            key = lambda p: p[1],
            reverse = True,
        )
        self._min_index = self._indexes[-1][1] if self._indexes else len(self._cards) - 1

    def redo(self):
        for _, idx in self._indexes:
            self._aligner.cards.pop(idx)

        self._aligner.realign(self._min_index)

    def undo(self):
        for card, idx in reversed(self._indexes):
            self._aligner.cards.insert(idx, card)

        self._aligner.realign(self._min_index)


class GridMultiDrop(AlignmentDrop):

    def __init__(self, aligner: GridAligner, drops: t.Sequence[t.Tuple[t.Sequence[PhysicalCard], int]]):
        self._aligner = aligner
        self._drops = drops

    def redo(self):
        for cards, idx in reversed(self._drops):
            self._aligner.cards[idx:idx] = cards

        self._aligner.realign(self._drops[0][1])

    def undo(self):
        for cards, idx in reversed(self._drops):
            del self._aligner.cards[idx:idx + len(cards)]

        self._aligner.realign(self._drops[0][1])


class GridSort(QUndoCommand):

    def __init__(self, grid: GridAligner, sort_property: SortProperty, original_order: t.List[PhysicalCard]):
        self._grid = grid
        self._sort_property = sort_property
        self._original_order = original_order
        super().__init__('grid sort')

    def redo(self) -> None:
        self._grid.cards[:] = sorted(
            self._original_order,
            key = lambda card: extract_sort_value(card.cubeable, self._sort_property),
        )
        self._grid.realign()

    def undo(self) -> None:
        self._grid.cards[:] = self._original_order
        self._grid.realign()


class GridAligner(Aligner):

    def __init__(self, scene: SelectionScene, margin: int = 10, columns: t.Optional[int] = None):
        super().__init__(scene)

        self._margin = margin
        self._columns = self._scene.width() // (IMAGE_WIDTH + self._margin) if columns is None else columns

        self._cards: t.List[PhysicalCard] = []

    @property
    def cards(self) -> t.List[PhysicalCard]:
        return self._cards

    def pick_up(self, items: t.Iterable[PhysicalCard]) -> GridPickUp:
        return GridPickUp(
            self,
            items,
        )

    def get_position_at_index(self, idx: int) -> QPoint:
        return QPoint(
            max(
                min(
                    (idx % self._columns) * (IMAGE_WIDTH + self._margin),
                    self._scene.width() - IMAGE_WIDTH
                ),
                0
            ),
            max(
                min(
                    (idx // self._columns) * (IMAGE_HEIGHT + self._margin),
                    self._scene.height() - IMAGE_HEIGHT
                ),
                0
            ),
        )

    def map_position_to_index(self, position: QPoint) -> int:
        return int(
            position.x() // (SizeSlug.ORIGINAL.get_size(False)[0] + self._margin)
            + (position.y() // (SizeSlug.ORIGINAL.get_size(False)[1] + self._margin) * self._columns
               )
        )

    def realign(self, from_index: int = 0) -> None:
        for card, idx in zip(self._cards[from_index:], range(from_index, len(self._cards))):
            card.setPos(
                self.get_position_at_index(
                    idx
                )
            )

    def drop(self, items: t.Iterable[PhysicalCard], position: QPoint) -> GridDrop:
        return GridDrop(
            self,
            items,
            self.map_position_to_index(position)
        )

    def multi_drop(self, drops: t.Iterable[t.Tuple[t.Sequence[PhysicalCard], QPoint]]) -> GridMultiDrop:
        return GridMultiDrop(
            self,
            sorted(
                (
                    (cards, self.map_position_to_index(point))
                    for cards, point in
                    drops
                ),
                key = lambda p: p[1],
            )
        )

    def sort(self, sort_property: SortProperty, orientation: int) -> QUndoCommand:
        return GridSort(
            self,
            sort_property,
            copy.copy(self._cards),
        )
