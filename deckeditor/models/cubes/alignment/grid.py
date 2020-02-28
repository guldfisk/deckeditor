from __future__ import annotations

import copy
import typing as t
from abc import abstractmethod

from PyQt5 import QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoCommand, QUndoStack

from deckeditor.models.cubes.alignment.aligner import Aligner, AlignmentDrop
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.sorting.sorting import SortProperty
from deckeditor.values import IMAGE_WIDTH, IMAGE_HEIGHT
from mtgimg.interface import SizeSlug



class GridAlignmentCommandMixin(object):

    def __init__(self) -> None:
        super().__init__()
        self._is_setup: bool = False

    def _setup(self) -> None:
        pass

    @abstractmethod
    def _redo(self) -> None:
        pass

    def redo(self):
        if not self._is_setup:
            self._setup()
            self._is_setup = True
        self._redo()


class GridDrop(GridAlignmentCommandMixin, AlignmentDrop):
    _idx: int

    def __init__(self, aligner: GridAligner, cards: t.Iterable[PhysicalCard], pos: QPoint):
        super().__init__()
        self._aligner = aligner
        self._cards = list(cards)
        self._pos = pos

    def _setup(self) -> None:
        self._idx = self._aligner.map_position_to_index(self._pos)

    def _redo(self) -> None:
        self._aligner.cards[self._idx:self._idx] = self._cards
        self._aligner.realign(self._idx)

    def undo(self):
        del self._aligner.cards[self._idx:self._idx + len(self._cards)]
        self._aligner.realign(self._idx)


class GridPickUp(GridAlignmentCommandMixin, AlignmentDrop):
    _indexes: t.List[t.Tuple[PhysicalCard, int]]
    _min_index: int

    def __init__(self, aligner: GridAligner, cards: t.Iterable[PhysicalCard]):
        super().__init__()
        self._aligner = aligner
        self._cards = list(cards)

    def _setup(self) -> None:
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

    def _redo(self) -> None:
        for _, idx in self._indexes:
            self._aligner.cards.pop(idx)

        self._aligner.realign(self._min_index)

    def undo(self):
        for card, idx in reversed(self._indexes):
            self._aligner.cards.insert(idx, card)

        self._aligner.realign(self._min_index)


class GridMultiDrop(GridAlignmentCommandMixin, AlignmentDrop):
    _drops: t.Sequence[t.Tuple[t.Sequence[PhysicalCard], int]]

    def __init__(self, aligner: GridAligner, drops: t.Sequence[t.Tuple[t.Sequence[PhysicalCard], QPoint]]):
        super().__init__()
        self._aligner = aligner
        self._raw_drops = drops

    def _setup(self):
        self._drops = sorted(
            (
                (cards, self._aligner.map_position_to_index(point))
                for cards, point in
                self._raw_drops
            ),
            key = lambda p: p[1],
        )

    def _redo(self):
        if not self._drops:
            return

        for cards, idx in reversed(self._drops):
            self._aligner.cards[idx:idx] = cards

        self._aligner.realign(self._drops[0][1])

    def undo(self):
        if not self._drops:
            return

        for cards, idx in reversed(self._drops):
            del self._aligner.cards[idx:idx + len(cards)]

        self._aligner.realign(self._drops[0][1])


class GridSort(QUndoCommand):

    def __init__(
        self,
        grid: GridAligner,
        sort_property: t.Type[SortProperty],
        cards: t.Sequence[PhysicalCard],
        original_order: t.List[PhysicalCard],
        in_place: bool,
    ):
        self._grid = grid
        self._cards = cards
        self._sort_property = sort_property
        self._original_order = original_order
        self._in_place = in_place
        super().__init__('grid sort')

    def redo(self) -> None:
        sorted_cards = sorted(
            self._cards,
            key = lambda card: self._sort_property.extract(card.cubeable),
        )
        unsorted_cards = [card for card in self._original_order if not card in self._cards]
        if not self._in_place:
            self._grid.cards[:] = sorted_cards + unsorted_cards
        else:
            self._grid.cards[:] = unsorted_cards
            idx = next(idx for idx, card in enumerate(self._original_order) if card in self._cards)
            self._grid.cards[idx:idx] = sorted_cards
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
                    self._scene.width() - IMAGE_WIDTH,
                ),
                0,
            ),
            max(
                min(
                    (idx // self._columns) * (IMAGE_HEIGHT + self._margin),
                    self._scene.height() - IMAGE_HEIGHT,
                ),
                0,
            ),
        )

    def map_position_to_index(self, position: QPoint) -> int:
        return min(
            int(
                position.x() // (IMAGE_WIDTH + self._margin)
                + (
                    position.y() // (IMAGE_HEIGHT + self._margin) * self._columns
                )
            ),
            len(self._cards),
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
            position,
        )

    def multi_drop(self, drops: t.Sequence[t.Tuple[t.Sequence[PhysicalCard], QPoint]]) -> GridMultiDrop:
        return GridMultiDrop(
            self,
            drops,
        )

    def sort(
        self,
        sort_property: t.Type[SortProperty],
        cards: t.Sequence[PhysicalCard],
        orientation: int,
        in_place: bool = False,
    ) -> QUndoCommand:
        return GridSort(
            self,
            sort_property,
            cards,
            copy.copy(self._cards),
            in_place,
        )

    def context_menu(self, menu: QtWidgets.QMenu, position: QPoint, undo_stack: QUndoStack) -> None:
        pass
