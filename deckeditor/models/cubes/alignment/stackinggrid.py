from __future__ import annotations

import math
import typing as t
from abc import abstractmethod, ABC
from collections import defaultdict

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QPoint, QLineF
from PyQt5.QtWidgets import QUndoCommand, QUndoStack, QDialogButtonBox

from hardcandy import fields
from hardcandy.schema import Schema

from deckeditor.models.cubes.alignment.aligner import AlignmentPickUp, AlignmentDrop, Aligner
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.sorting import sorting
from deckeditor.sorting.sorting import SortIdentity, SortMacro, SortDimension, DimensionContinuity
from deckeditor.store.models import SortSpecification
from deckeditor.utils.math import minmax
from deckeditor.utils.undo import CommandPackage
from deckeditor.values import IMAGE_WIDTH, STANDARD_IMAGE_MARGIN


class GridResizeDialog(QtWidgets.QDialog):

    def __init__(self, aligner: StackingGrid):
        super().__init__()

        self._aligner = aligner

        self._columns_selector = QtWidgets.QSpinBox()
        self._columns_selector.setValue(aligner.stacker_map.row_length)

        self._rows_selector = QtWidgets.QSpinBox()
        self._rows_selector.setValue(aligner.stacker_map.column_height)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        for selector in (
            self._columns_selector,
            self._rows_selector,
        ):
            selector.setRange(1, 64)

        layout = QtWidgets.QFormLayout(self)

        layout.addRow('columns', self._columns_selector)
        layout.addRow('rows', self._rows_selector)
        layout.addWidget(self._buttons)

    def get_values(self) -> t.Tuple[int, int]:
        return (
            self._columns_selector.value(),
            self._rows_selector.value(),
        )


class CardStacker(ABC):

    def __init__(
        self,
        aligner: StackingGrid,
        index: t.Sequence[int],
    ):
        self._aligner: StackingGrid = aligner
        self._index: t.List[int] = list(index)

        self._cards: t.List[PhysicalCard] = []

        self._requested_size: t.Tuple[float, float] = 0., 0.

    @property
    def grid(self) -> StackingGrid:
        return self._aligner

    @property
    def index(self) -> t.List[int]:
        return self._index

    @property
    def x_index(self) -> int:
        return self._index[0]

    @property
    def y_index(self) -> int:
        return self._index[1]

    @property
    def x(self) -> float:
        return self._aligner.stacker_map.width_at(self.x_index)

    @property
    def y(self) -> float:
        return self._aligner.stacker_map.height_at(self.y_index)

    @property
    def position(self) -> t.Tuple[float, float]:
        return self.x, self.y

    @property
    def width(self) -> float:
        return self._aligner.stacker_map.column_width_at(self.x_index)

    @property
    def height(self) -> float:
        return self._aligner.stacker_map.row_height_at(self.y_index)

    @property
    def size(self) -> t.Tuple[float, float]:
        return self.width, self.height

    @property
    def requested_size(self) -> t.Tuple[float, float]:
        return self._requested_size

    @property
    def requested_width(self) -> float:
        return self._requested_size[0]

    @property
    def requested_height(self) -> float:
        return self._requested_size[1]

    @property
    def cards(self) -> t.List[PhysicalCard]:
        return self._cards

    @abstractmethod
    def map_position_to_index(self, x: float, y: float) -> int:
        pass

    @abstractmethod
    def calculate_requested_size(self) -> t.Tuple[float, float]:
        pass

    def update(self, external: bool = False):
        if not external:
            self._requested_size = self.calculate_requested_size()
            self._aligner.request_space(self, *self.requested_size)

        self._stack()

        for index, card in enumerate(self._cards):
            card.setZValue(index - len(self._cards) - 1)
            self._aligner.get_card_info(card).position = index

    @abstractmethod
    def _stack(self):
        pass

    def add_card_no_restack(self, card: PhysicalCard):
        info = self._aligner.get_card_info(card)

        if info.card_stacker is not None:
            info.card_stacker.remove_cards((card,))

        info.card_stacker = self
        self._cards.append(card)

    def _remove_card_no_restack(self, card: PhysicalCard):
        self._cards.remove(card)
        self._aligner.remove_card(card)

    def _insert_card_no_restack(self, index: int, card: PhysicalCard):
        info = self._aligner.get_card_info(card)

        if info.card_stacker is not None:
            info.card_stacker.remove_cards((card,))

        info.card_stacker = self
        self._cards.insert(index, card)

    def insert_card(self, index: int, card: PhysicalCard):
        self._insert_card_no_restack(index, card)
        self.update()

    def remove_cards(self, cards: t.Iterable[PhysicalCard]):
        for card in cards:
            self._remove_card_no_restack(card)

        self.update()

    def remove_cards_no_restack(self, cards: t.Iterable[PhysicalCard]) -> None:
        for card in cards:
            self._remove_card_no_restack(card)

    def add_cards(self, cards: t.Iterable[PhysicalCard]):
        for card in cards:
            self.add_card_no_restack(card)
        self.update()

    def add_cards_no_restack(self, cards: t.Iterable[PhysicalCard]):
        for card in cards:
            self.add_card_no_restack(card)

    def insert_cards(self, indexes: t.Iterable[int], cards: t.Iterable[PhysicalCard]):
        for index, card in zip(indexes, cards):
            self._insert_card_no_restack(index, card)
        self.update()

    def clear_no_restack(self):
        for card in self._cards:
            self._aligner.remove_card(card)
        self._cards.clear()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({id(self)})'


class StackingDrop(AlignmentPickUp):

    def __init__(
        self,
        grid: StackingGrid,
        stacker: CardStacker,
        index: int,
        cards: t.Tuple[PhysicalCard, ...],
    ):
        self._grid = grid
        self._stacker = stacker
        self._index = index
        self._cards = cards

    def redo(self):
        self._stacker.insert_cards(
            range(self._index, self._index + len(self._cards)),
            self._cards,
        )

    def undo(self):
        self._stacker.remove_cards(self._cards)


class StackingMultiDrop(AlignmentPickUp):

    def __init__(
        self,
        grid: StackingGrid,
        drops: t.Sequence[t.Tuple[t.Sequence[PhysicalCard], CardStacker, int]],
    ):
        self._grid = grid
        self._drops = drops

    def redo(self):
        for cards, stacker, idx in self._drops:
            stacker.insert_cards(
                range(idx, idx + len(cards)),
                cards,
            )

    def undo(self):
        for cards, stacker, idx in self._drops:
            stacker.remove_cards(cards)


class StackingPickUp(AlignmentDrop):

    def __init__(
        self,
        grid: StackingGrid,
        cards: t.Iterable[PhysicalCard],
    ):
        self._grid = grid
        self._stacker_map: t.MutableMapping[CardStacker, t.List[t.Tuple[int, PhysicalCard]]] = defaultdict(list)

        for card in cards:
            info = self._grid.get_card_info(card)
            self._stacker_map[info.card_stacker].append(
                (info.position, card)
            )

    def redo(self):
        for stacker, cards in self._stacker_map.items():
            if stacker:
                stacker.remove_cards(
                    card
                    for position, card in
                    cards
                )

    def undo(self):
        for stacker, infos in self._stacker_map.items():
            _infos = sorted(infos, key = lambda info: info[0])

            adjusted_indexes = []
            passed = 0

            for index, card in _infos:
                adjusted_indexes.append((index - passed, card))
                passed += 1

            stacker.insert_cards(*zip(*reversed(adjusted_indexes)))


class SortStacker(QUndoCommand):

    def __init__(self, stacker: CardStacker, specifications: t.Sequence[SortSpecification]):
        self._stacker = stacker
        self._specifications = specifications
        super().__init__('Sort stacker')

        self._original_order: t.List[PhysicalCard] = []

    def redo(self) -> None:
        if not self._original_order:
            self._original_order[:] = self._stacker.cards

        self._stacker.cards[:] = sorted(
            self._stacker.cards,
            key = lambda card: SortIdentity.for_cubeable(card.cubeable, self._specifications),
        )
        self._stacker.update()

    def undo(self) -> None:
        self._stacker.cards[:] = self._original_order
        self._stacker.update()


class SortAllStackers(QUndoCommand):

    def __init__(self, grid: StackingGrid, specifications: t.Sequence[SortSpecification]):
        self._grid = grid
        self._specifications = specifications
        super().__init__('Sort all stacker')

        self._original_orders: t.MutableMapping[CardStacker, t.List[PhysicalCard]] = defaultdict(list)

    def redo(self) -> None:
        if not self._original_orders:
            for stacker in self._grid.stacker_map.stackers:
                self._original_orders[stacker][:] = stacker.cards

        for stacker in self._grid.stacker_map.stackers:
            stacker.cards[:] = sorted(
                stacker.cards,
                key = lambda card: SortIdentity.for_cubeable(card.cubeable, self._specifications),
            )
            stacker.update()

    def undo(self) -> None:
        for stacker, cards in self._original_orders.items():
            stacker.cards[:] = cards
            stacker.update()


class ContinuousSort(QUndoCommand):

    def __init__(
        self,
        grid: StackingGrid,
        cards: t.Sequence[PhysicalCard],
        specifications: t.Sequence[SortSpecification],
        orientation: int,
        in_place: bool,
    ):
        self._grid = grid
        self._cards = cards
        self._specifications = specifications
        self._orientation = orientation
        self._in_place = in_place

        self._smallest_index: int = 0
        self._card_infos: t.Dict[PhysicalCard, t.Tuple[CardStacker, int]] = {}
        self._stackers: t.MutableMapping[CardStacker, t.List[t.Tuple[int, PhysicalCard]]] = defaultdict(list)
        self._sorted_stackers: t.MutableMapping[CardStacker, t.List[PhysicalCard]] = defaultdict(list)

        super().__init__('Sort')

    def _init(self):
        for card in self._cards:
            info = self._grid.get_card_info(card)
            self._stackers[info.card_stacker].append((info.position, card))
            self._card_infos[card] = (info.card_stacker, info.position)

    def _sorted_cards(self) -> t.List[PhysicalCard]:
        return sorted(
            self._card_infos.keys(),
            key = lambda card: SortIdentity.for_cubeable(card.cubeable, self._specifications),
        )

    @property
    def _cards_separated(self) -> t.Generator[t.Tuple[PhysicalCard, int]]:
        sorted_cards = self._sorted_cards()

        parts = (
            self._grid.stacker_map.row_length
            if self._orientation == QtCore.Qt.Horizontal else
            self._grid.stacker_map.column_height
        )

        part = math.ceil(len(sorted_cards) / parts)

        sorted_cards_iter = sorted_cards.__iter__()

        try:
            for i in range(parts):
                for n in range(part):
                    yield next(sorted_cards_iter), i
        except StopIteration:
            return

    def _card_sorted_indexes(self) -> t.Iterator[t.Tuple[PhysicalCard, int, int]]:
        info_extractor = (
            (lambda _i, info: (_i + self._smallest_index, info[0].index[1]))
            if self._orientation == QtCore.Qt.Horizontal else
            (lambda _i, info: (info[0].index[0], _i + self._smallest_index))
        )

        for card, i in self._cards_separated:
            yield card, *info_extractor(i, self._card_infos[card])

    def _make_sorted_stackers(self) -> None:
        for card, x, y in self._card_sorted_indexes():
            self._sorted_stackers[self._grid.get_card_stacker_at_index(x, y)].append(card)

    def redo(self) -> None:
        if not self._card_infos:
            self._init()

        if self._in_place and not self._smallest_index:
            if self._orientation == QtCore.Qt.Horizontal:
                self._smallest_index = min(
                    stacker.x_index
                    for stacker in
                    self._stackers
                )
            else:
                self._smallest_index = min(
                    stacker.y_index
                    for stacker in
                    self._stackers
                )

        for stacker, cards in self._stackers.items():
            stacker.remove_cards_no_restack((card for _, card in cards))

        if not self._sorted_stackers:
            self._make_sorted_stackers()

        for stacker, cards in self._sorted_stackers.items():
            stacker.add_cards_no_restack(cards)

        for stacker in self._stackers.keys() | self._sorted_stackers.keys():
            stacker.update()

    def undo(self) -> None:
        for stacker, cards in self._sorted_stackers.items():
            stacker.remove_cards_no_restack(cards)

        for stacker, infos in self._stackers.items():
            stacker.add_cards(card for index, card in infos)

        for stacker in self._stackers.keys() | self._sorted_stackers.keys():
            stacker.update()


class GroupedSort(ContinuousSort):

    @property
    def _cards_separated(self) -> t.Iterable[t.Tuple[PhysicalCard, int]]:
        parts = (
            self._grid.stacker_map.row_length
            if self._orientation == QtCore.Qt.Horizontal else
            self._grid.stacker_map.column_height
        )

        value_map = defaultdict(list)

        for card in self._card_infos.keys():
            value_map[SortIdentity.for_cubeable(card.cubeable, self._specifications)].append(card)

        for key, cards, in value_map.items():
            value_map[key] = sorted(
                cards,
                key = lambda c: sorting.NameExtractor.extract(c.cubeable),
            )

        values = sorted(value_map.keys()).__iter__()

        for i in range(parts):
            value = next(values, None)
            if value is None:
                break

            for card in value_map[value]:
                yield card, i

        for value in values:
            for card in value_map[value]:
                yield card, parts - 1


class RowColumnInsert(QUndoCommand):

    def __init__(self, grid: StackingGrid, idx: int):
        super().__init__('Insert row/column')
        self._grid = grid
        self._idx = idx


class ColumnInsert(RowColumnInsert):

    def __init__(self, grid: StackingGrid, idx: int):
        super().__init__(grid, idx)

        if self._idx >= self._grid.stacker_map.row_length:
            self.setObsolete(True)

        self._stackers: t.List[t.List[t.List[PhysicalCard]]] = []

    def _setup(self):
        self._stackers = [
            [
                list(stacker.cards)
                for stacker in
                column
            ] for column in
            self._grid.stacker_map.columns[self._idx:-1]
        ]

    def redo(self) -> None:
        if not self._stackers:
            self._setup()

        for column in self._grid.stacker_map.columns[self._idx:-1]:
            for stacker in column:
                stacker.clear_no_restack()

        for x, column in enumerate(self._stackers):
            for y, cards in enumerate(column):
                self._grid.stacker_map.get_stacker(self._idx + x + 1, y).add_cards(cards)

    def undo(self) -> None:
        for x, column in enumerate(self._stackers):
            for y, cards in enumerate(column):
                self._grid.stacker_map.get_stacker(self._idx + x + 1, y).remove_cards_no_restack(cards)

        for x, column in enumerate(self._stackers):
            for y, cards in enumerate(column):
                self._grid.stacker_map.get_stacker(self._idx + x, y).add_cards(cards)


class RowInsert(RowColumnInsert):

    def __init__(self, grid: StackingGrid, idx: int):
        super().__init__(grid, idx)

        if self._idx >= self._grid.stacker_map.column_height:
            self.setObsolete(True)

        self._stackers: t.List[t.List[t.List[PhysicalCard]]] = []

    def _setup(self):
        self._stackers = [
            [
                list(stacker.cards)
                for stacker in
                rows
            ] for rows in
            list(self._grid.stacker_map.rows)[self._idx:-1]
        ]

    def redo(self) -> None:
        if not self._stackers:
            self._setup()

        for row in list(self._grid.stacker_map.rows)[self._idx:-1]:
            for stacker in row:
                stacker.clear_no_restack()

        for y, row in enumerate(self._stackers):
            for x, cards in enumerate(row):
                self._grid.stacker_map.get_stacker(x, self._idx + y + 1).add_cards(cards)

    def undo(self) -> None:
        for y, row in enumerate(self._stackers):
            for x, cards in enumerate(row):
                self._grid.stacker_map.get_stacker(x, self._idx + y + 1).remove_cards_no_restack(cards)

        for y, row in enumerate(self._stackers):
            for x, cards in enumerate(row):
                self._grid.stacker_map.get_stacker(x, self._idx + y).add_cards(cards)


class GridResize(QUndoCommand):

    def __init__(self, aligner: StackingGrid, rows: int, columns: int):
        super().__init__()
        self._aligner = aligner
        self._rows = rows
        self._columns = columns

        self._pick_up: t.Optional[StackingPickUp] = None
        self._old_map: t.Optional[StackerMap] = None
        self._new_map: t.Optional[StackerMap] = None
        self._drop: t.Optional[StackingMultiDrop] = None

    def redo(self):
        if self._old_map is None:
            self._old_map = self._aligner.stacker_map

        if self._new_map is None:
            self._new_map = self._aligner.create_stacker_map(self._rows, self._columns)

        if self._drop is None:
            self._drop = StackingMultiDrop(
                grid = self._aligner,
                drops = [
                    (
                        list(stacker.cards),
                        self._new_map.get_stacker_clipped(stacker.x_index, stacker.y_index),
                        0,
                    )
                    for stacker in
                    self._old_map.stackers
                ]
            )

        if self._pick_up is None:
            self._pick_up = StackingPickUp(grid = self._aligner, cards = list(self._aligner.scene.items()))

        self._pick_up.redo()
        self._aligner._stacker_map = self._new_map
        self._drop.redo()
        self._aligner.scene.update()

    def undo(self):
        self._drop.undo()
        self._aligner._stacker_map = self._old_map
        self._pick_up.undo()
        self._aligner.scene.update()


class _CardInfo(object):

    def __init__(self, stacker: t.Optional[CardStacker] = None, position: t.Optional[int] = None):
        self.card_stacker: t.Optional[CardStacker] = stacker
        self.position: t.Optional[int] = position

    def __repr__(self):
        return f'{self.__class__.__name__}({self.card_stacker, self.position})'


class StackerMap(object):

    def __init__(
        self,
        aligner: StackingGrid,
        row_amount: t.Optional[int] = None,
        column_amount: t.Optional[int] = None,
        default_column_width: float = 1.,
        default_row_height: float = 1.,
        *,
        grid: t.Optional[t.List[t.List[CardStacker]]] = None,
    ):
        self._aligner = aligner

        self._row_amount = row_amount
        self._column_amount = column_amount

        self._grid = (
            grid
            if grid is not None else
            [
                [
                    self._aligner.create_stacker(
                        row,
                        column,
                    )
                    for column in
                    range(row_amount)
                ]
                for row in
                range(column_amount)
            ]
        )

        self._row_heights = [
            default_row_height
            for _ in
            range(self._row_amount)
        ]
        self._column_widths = [
            default_column_width
            for _ in
            range(self._column_amount)
        ]

    @property
    def row_length(self) -> int:
        return self._column_amount

    @property
    def column_height(self) -> int:
        return self._row_amount

    @property
    def width(self) -> int:
        return sum(self._column_widths)

    @property
    def height(self) -> int:
        return sum(self._row_heights)

    @property
    def columns(self) -> t.List[t.List[CardStacker]]:
        return self._grid

    def column_at(self, index: int) -> t.List[CardStacker]:
        return self._grid[index]

    @property
    def rows(self) -> t.Iterator[t.Tuple[CardStacker, ...]]:
        return zip(*self._grid)

    def row_at(self, index: int) -> t.Iterable[CardStacker]:
        for column in self._grid:
            yield column[index]

    def width_at(self, index: int) -> int:
        return sum(self._column_widths[:index])

    def height_at(self, index: int) -> int:
        return sum(self._row_heights[:index])

    def row_height_at(self, index: int) -> float:
        return self._row_heights[index]

    def set_row_height_at(self, index: int, height: float) -> None:
        self._row_heights[index] = height

    def column_width_at(self, index: int) -> float:
        return self._column_widths[index]

    def set_column_width_at(self, index: int, width: float) -> None:
        self._column_widths[index] = width

    def row_termination_points(self) -> t.Iterator[int]:
        v = 0
        for i in range(self.row_length):
            v += self.column_width_at(i)
            yield v

    def column_termination_points(self) -> t.Iterator[int]:
        v = 0
        for i in range(self.column_height):
            v += self.row_height_at(i)
            yield v

    def map_position_to_index(self, x: float, y: float) -> t.Tuple[int, int]:
        xi = self.row_length
        for i in range(self.row_length):
            if x <= self.column_width_at(i):
                xi = i
                break
            x -= self.column_width_at(i)

        yi = self.column_height
        for i in range(self.column_height):
            if y <= self.row_height_at(i):
                yi = i
                break
            y -= self.row_height_at(i)

        return xi, yi

    def get_stacker(self, x: int, y: int) -> CardStacker:
        return self._grid[x][y]

    def get_stacker_clipped(self, x: int, y: int) -> CardStacker:
        return self._grid[min(x, self.row_length - 1)][min(y, self.column_height - 1)]

    @property
    def stackers(self) -> t.Iterator[CardStacker]:
        for column in self._grid:
            for stacker in column:
                yield stacker

    def __iter__(self) -> t.Iterator[CardStacker]:
        return self.stackers

    def __str__(self):
        return '[\n' + '\n'.join(
            '\t[' + ', '.join(
                # '({}, {})'.format(*(round(v, 3) for v in cell.position))
                str(len(cell.cards))
                for cell in
                row
            ) + ']'
            for row in
            zip(*self._grid)
        ) + '\n]'


class StackingGrid(Aligner):
    _show_grid = False
    schema = Schema(
        fields = {
            'rows': fields.Integer(default = 3, min = 1, max = 64),
            'columns': fields.Integer(default = 15, min = 1, max = 64),
            # 'margin': fields.Float(default = STANDARD_IMAGE_MARGIN, min = 0., max = 1.),
            'show_grid': fields.Bool(default = False),
        },
    )

    def __init__(
        self,
        scene: SelectionScene,
        *,
        rows: int = 5,
        columns: int = 5,
        margin: float = STANDARD_IMAGE_MARGIN,
        show_grid: bool = False,
    ):
        super().__init__(scene)

        self._stacked_cards: t.Dict[PhysicalCard, _CardInfo] = {}
        self._margin_pixel_size = margin * IMAGE_WIDTH
        self._stacker_map = self.create_stacker_map(rows, columns)
        self._show_grid = show_grid

    @property
    def options(self) -> t.Mapping[str, t.Any]:
        return {
            'rows': self._stacker_map.column_height,
            'columns': self._stacker_map.row_length,
            'show_grid': self._show_grid,
        }

    @abstractmethod
    def create_stacker_map(self, rows: int, columns: int) -> StackerMap:
        pass

    @abstractmethod
    def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
        pass

    @abstractmethod
    def create_stacker(self, x: int, y: int) -> CardStacker:
        pass

    @property
    def stacker_map(self) -> StackerMap:
        return self._stacker_map

    @property
    def stacked_cards(self) -> t.Dict[PhysicalCard, _CardInfo]:
        return self._stacked_cards

    @property
    def cards(self) -> t.Iterable[PhysicalCard]:
        for stacker in self._stacker_map.stackers:
            yield from stacker.cards

    def realign(self) -> None:
        for stacker in self._stacker_map:
            stacker.update()

    def get_card_info(self, card: PhysicalCard) -> _CardInfo:
        try:
            return self._stacked_cards[card]
        except KeyError:
            self._stacked_cards[card] = info = _CardInfo()
            return info

    def remove_card(self, card: PhysicalCard) -> None:
        try:
            del self._stacked_cards[card]
        except KeyError:
            pass

    def pick_up(self, items: t.Iterable[PhysicalCard]) -> StackingPickUp:
        return StackingPickUp(
            self,
            items,
        )

    def drop(self, items: t.Iterable[PhysicalCard], position: QPoint) -> StackingDrop:
        x, y = position.x(), position.y()
        stacker = self.get_card_stacker(x, y)
        index = stacker.map_position_to_index(x - stacker.x, y - stacker.y)
        return StackingDrop(
            self,
            stacker,
            index,
            tuple(items),
        )

    def multi_drop(self, drops: t.Iterable[t.Tuple[t.Sequence[PhysicalCard], QPoint]]) -> StackingMultiDrop:
        _drops = []
        for cards, position in drops:
            x, y = position.x(), position.y()
            stacker = self.get_card_stacker(x, y)
            index = stacker.map_position_to_index(x - stacker.x, y - stacker.y)
            _drops.append(
                (
                    cards,
                    stacker,
                    index,
                )
            )

        return StackingMultiDrop(self, _drops)

    def get_card_stacker_at_index(self, x: int, y: int) -> CardStacker:
        return self.stacker_map.get_stacker(
            minmax(0, x, self.stacker_map.row_length - 1),
            minmax(0, y, self.stacker_map.column_height - 1),
        )

    def get_card_stacker(self, x: int, y: int) -> CardStacker:
        return self.get_card_stacker_at_index(
            *self._stacker_map.map_position_to_index(x, y)
        )

    def sort(self, sort_macro: SortMacro, cards: t.Sequence[PhysicalCard], in_place: bool = False) -> QUndoCommand:
        commands = []
        for dimension, specifications in sort_macro.dimension_specifications_map:
            continuity = sort_macro.continuity_for_dimension(dimension)
            if continuity == DimensionContinuity.AUTO:
                if len(specifications) == 1:
                    continuity = continuity.continuity_for(specifications[0].sort_property)
                else:
                    continuity = DimensionContinuity.CONTINUOUS

            if dimension == SortDimension.SUB_DIVISIONS:
                commands.append(
                    SortAllStackers(
                        grid = self,
                        specifications = specifications,
                    )
                )

            else:
                commands.append(
                    (
                        ContinuousSort
                        if continuity == DimensionContinuity.CONTINUOUS else
                        GroupedSort
                    )(
                        grid = self,
                        cards = cards,
                        specifications = specifications,
                        orientation = QtCore.Qt.Horizontal if dimension == SortDimension.HORIZONTAL else QtCore.Qt.Vertical,
                        in_place = in_place,
                    )
                )

        if len(commands) == 1:
            return commands[0]

        return CommandPackage(commands)

    @classmethod
    def _get_sort_stack(
        cls,
        stacker: CardStacker,
        sort_property: t.Type[sorting.SortProperty],
        undo_stack: QUndoStack,
    ) -> t.Callable[[], None]:
        def _sort_stack() -> None:
            undo_stack.push(
                SortStacker(
                    stacker = stacker,
                    specifications = [sorting.SortSpecification(sort_property = sort_property)],
                )
            )

        return _sort_stack

    def _get_all_sort_stacker(
        self,
        sort_property: t.Type[sorting.SortProperty],
        undo_stack: QUndoStack,
    ) -> t.Callable[[], None]:
        def _sort_all_stackers() -> None:
            undo_stack.push(
                SortAllStackers(
                    grid = self,
                    specifications = [sorting.SortSpecification(sort_property = sort_property)],
                )
            )

        return _sort_all_stackers

    def insert_row(self, idx: int) -> QUndoCommand:
        pass

    def insert_column(self, idx: int) -> QUndoCommand:
        pass

    def _set_show_grid(self, show_grid: bool) -> None:
        self._show_grid = show_grid

    def context_menu(self, menu: QtWidgets.QMenu, position: QPoint, undo_stack: QUndoStack) -> None:
        stacker = self.get_card_stacker(position.x(), position.y())

        stacker_sort_menu = menu.addMenu('Sort Stack')

        for sort_property in sorting.SortProperty.names_to_sort_property.values():
            sort_action = QtWidgets.QAction(sort_property.name, stacker_sort_menu)
            sort_action.triggered.connect(self._get_sort_stack(stacker, sort_property, undo_stack))
            stacker_sort_menu.addAction(sort_action)

        all_stacker_sort_menu = menu.addMenu('Sort All Stack')

        for sort_property in sorting.SortProperty.names_to_sort_property.values():
            all_sort_action = QtWidgets.QAction(sort_property.name, all_stacker_sort_menu)
            all_sort_action.triggered.connect(self._get_all_sort_stacker(sort_property, undo_stack))
            all_stacker_sort_menu.addAction(all_sort_action)

        resize_action = QtWidgets.QAction('Resize grid', menu)
        resize_action.triggered.connect(lambda: self.resize(undo_stack))
        menu.addAction(resize_action)

        toggle_grid_action = QtWidgets.QAction('Hide Grid' if self._show_grid else 'Show Grid', menu)
        toggle_grid_action.triggered.connect(lambda: self._set_show_grid(not self._show_grid))
        menu.addAction(toggle_grid_action)

    def resize(self, undo_stack: QUndoStack) -> None:
        dialog = GridResizeDialog(self)
        dialog.exec_()
        if dialog.accepted:
            undo_stack.push(
                GridResize(
                    self,
                    *reversed(dialog.get_values()),
                )
            )

    def draw_background(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        if not self._show_grid:
            return

        painter.setPen(
            QtGui.QPen(
                QtGui.QColor(0, 0, 0)
            )
        )

        lines = []

        for x in list(self.stacker_map.row_termination_points())[:-1]:
            if rect.left() <= x <= rect.right():
                lines.append(
                    QLineF(
                        x, rect.top(), x, rect.bottom(),
                    )
                )

        for y in list(self.stacker_map.column_termination_points())[:-1]:
            if rect.top() <= y <= rect.bottom():
                lines.append(
                    QLineF(
                        rect.left(), y, rect.right(), y,
                    )
                )

        painter.drawLines(lines)
