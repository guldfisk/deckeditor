from __future__ import annotations

import math
import typing as t
from collections import defaultdict

from itertools import chain
from abc import abstractmethod, ABC

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoCommand, QUndoStack

from deckeditor.sorting import sorting
from mtgorp.models.persistent.attributes import typeline, colors

from mtgorp.models.persistent.printing import Printing

from mtgimg.interface import IMAGE_SIZE_MAP, SizeSlug

from magiccube.collections import cubeable as Cubeable

from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.context.context import Context
from deckeditor.values import Direction
from deckeditor.models.cubes.alignment.aligner import AlignmentPickUp, AlignmentDrop, Aligner
from deckeditor.models.cubes.selection import SelectionScene

IMAGE_WIDTH, IMAGE_HEIGHT = IMAGE_SIZE_MAP[frozenset((SizeSlug.ORIGINAL, False))]


class CardStacker(ABC):

    def __init__(
        self,
        aligner: StackingGrid,
        index: t.Sequence[int],
    ):
        self._aligner: StackingGrid = aligner
        self._index: t.List[int] = list(index)

        self._cards: t.List[PhysicalCard] = []

        self._requested_size: t.Tuple[float, float] = (0., 0.)

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

    def update(self):
        self._aligner.request_space(self, *self.requested_size)
        self._stack()

        for index, card in enumerate(self._cards):
            # if card == self._aligner.cursor_position:
            #     self._aligner.scene.cursor.setPos(
            #         card.pos()
            #     )

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
        # cards = list(cards)

        # cursor_info = self._aligner.get_card_info(self._aligner.cursor_position)

        for card in cards:
            self._remove_card_no_restack(card)

        self.update()

        # if self._aligner.cursor_position in cards:
        #     if cursor_info.card_stacker.cards:
        #         self._aligner.link_cursor(
        #             cursor_info.card_stacker.cards[
        #                 min(
        #                     len(cursor_info.card_stacker.cards) - 1,
        #                     cursor_info.position,
        #                 )
        #             ]
        #         )
        #     else:
        #         stacker = self._aligner.find_stacker(
        #             *cursor_info.card_stacker.index,
        #             direction = Direction.UP
        #         )
        #         if stacker:
        #             self._aligner.link_cursor(stacker.cards[-1])
        #         else:
        #             self._aligner.link_cursor(None)

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

    # def persist(self) -> t.Any:
    #     return [
    #         card.persist()
    #         for card in
    #         self._cards
    #     ]
    #
    # def load(self, state: t.Any):
    #     self._cards = [
    #         PhysicalCard
    #     ]


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
                    (
                        card
                        for position, card in
                        cards
                    )
                )

    def undo(self):
        for stacker, infos in self._stacker_map.items():
            _infos = sorted(infos, key = lambda info: info[0])

            adjusted_indexes = []
            passed = 0

            for index, card in _infos:
                adjusted_indexes.append((index - passed, card))
                passed += 1

            stacker.insert_cards(*zip(*adjusted_indexes))


class SortStacker(QUndoCommand):

    def __init__(self, stacker: CardStacker, sort_property: t.Type[sorting.SortProperty]):
        self._stacker = stacker
        self._sort_property = sort_property
        super().__init__('Sort stacker')

        self._original_order: t.List[PhysicalCard] = []

    def redo(self) -> None:
        if not self._original_order:
            self._original_order[:] = self._stacker.cards

        self._stacker.cards[:] = sorted(
            self._stacker.cards,
            key = lambda card: self._sort_property.extract(card.cubeable),
        )
        self._stacker.update()

    def undo(self) -> None:
        self._stacker.cards[:] = self._original_order
        self._stacker.update()


class _StackingSort(QUndoCommand):
    sort_property_extractor: t.Type[sorting.SortProperty]

    def __init__(self, grid: StackingGrid, cards: t.Sequence[PhysicalCard], orientation: int, in_place: bool):
        self._grid = grid
        self._cards = cards
        self._orientation = orientation
        self._in_place = in_place

        self._smallest_index: int = 0
        self._card_infos: t.Dict[PhysicalCard, t.Tuple[CardStacker, int]] = {}
        self._stackers: t.MutableMapping[CardStacker, t.List[t.Tuple[int, PhysicalCard]]] = defaultdict(list)
        self._sorted_stackers: t.MutableMapping[CardStacker, t.List[PhysicalCard]] = defaultdict(list)

        for card in self._cards:
            info = self._grid.get_card_info(card)
            self._stackers[info.card_stacker].append((info.position, card))
            self._card_infos[card] = (info.card_stacker, info.position)

        super().__init__('Sort')

    def _sorted_cards(self) -> t.List[PhysicalCard]:
        return sorted(
            sorted(
                self._card_infos.keys(),
                key = lambda card: sorting.NameExtractor.extract(card.cubeable),
            ),
            key = lambda card: self.sort_property_extractor.extract(card.cubeable),
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
            (lambda i, info: (i + self._smallest_index, info[0].index[1]))
            if self._orientation == QtCore.Qt.Horizontal else
            (lambda i, info: (info[0].index[0], i + self._smallest_index))
        )

        for card, i in self._cards_separated:
            yield (card, *info_extractor(i, self._card_infos[card]))

    def _make_sorted_stackers(self) -> None:
        for card, x, y in self._card_sorted_indexes():
            self._sorted_stackers[self._grid.get_card_stacker_at_index(x, y)].append(card)

    def redo(self) -> None:
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


class _ValueToPositionSort(_StackingSort):

    def _sort_value(self, card: PhysicalCard) -> t.Union[str, int]:
        return self.sort_property_extractor.extract(card.cubeable)

    @property
    def _cards_separated(self) -> t.Iterable[t.Tuple[PhysicalCard, int]]:
        parts = (
            self._grid.stacker_map.row_length
            if self._orientation == QtCore.Qt.Horizontal else
            self._grid.stacker_map.column_height
        )

        value_map = defaultdict(list)

        for card in self._card_infos.keys():
            value_map[self._sort_value(card)].append(card)

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


class CmcSort(_ValueToPositionSort):
    sort_property_extractor = sorting.CMCExtractor


class IsCreatureSplit(_ValueToPositionSort):
    sort_property_extractor = sorting.IsCreatureExtractor


class IsLandSplit(_ValueToPositionSort):
    sort_property_extractor = sorting.IsLandExtractor


class IsMonoSplit(_ValueToPositionSort):
    sort_property_extractor = sorting.IsMonoExtractor


class RaritySort(_ValueToPositionSort):
    sort_property_extractor = sorting.RarityExtractor


class ColorSort(_ValueToPositionSort):
    sort_property_extractor = sorting.ColorExtractor


class CubeableTypeSort(_ValueToPositionSort):
    sort_property_extractor = sorting.CubeableTypeExtractor


class ColorIdentitySort(_ValueToPositionSort):
    sort_property_extractor = sorting.ColorIdentityExtractor


class NameSort(_StackingSort):

    def _sorted_cards(self) -> t.List[PhysicalCard]:
        return sorted(
            self._card_infos.keys(),
            key = lambda card: sorting.NameExtractor.extract(card.cubeable),
        )


class ExpansionSort(_ValueToPositionSort):
    sort_property_extractor = sorting.ExpansionExtractor


class CollectorsNumberSort(_StackingSort):
    sort_property_extractor = sorting.CollectorNumberExtractor


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

    # TODO fix
    # @property
    # def columns(self) -> t.List[t.List[CardStacker]]:
    #     return self._grid
    #
    # @property
    # def rows(self) -> t.Iterator[t.Tuple[CardStacker, ...]]:
    #     return zip(*self._grid)

    def width_at(self, index: int) -> int:
        return sum(self._column_widths[:index])

    def height_at(self, index: int) -> int:
        return sum(self._row_heights[:index])

    def row_height_at(self, index: int) -> float:
        return self._row_heights[index]

    def column_width_at(self, index: int) -> float:
        return self._column_widths[index]

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

    @property
    def stackers(self) -> t.Iterator[CardStacker]:
        for column in self._grid:
            for stacker in column:
                yield stacker

    # @classmethod
    # def _inflate(
    #     cls,
    #     aligner: StackingGrid,
    #     row_amount: int,
    #     column_amount: int,
    #     row_heights: t.List[float],
    #     column_widths: t.List[float],
    #     grid: t.
    # ):
    #     stacker_map = cls.__new__(cls)
    #
    #
    # def __reduce__(self):


    # def persist(self) -> t.Any:
    #     return [
    #         [
    #             stacker.persist()
    #             for stacker in
    #             row
    #         ]
    #         for row in
    #         self._grid
    #     ]
    #
    # def _load_stacker(self, x: int, y: int, state: t.Any):
    #
    # @classmethod
    # def load(cls, state: t.Any, aligner: StackingGrid) -> StackerMap:
    #     # create_stacker: t.Callable[[int, int], CardStacker]
    #     return StackerMap(
    #         aligner,
    #         grid = [
    #             [
    #                 aligner.create_stacker(x, y)
    #                 for x, stacker in
    #                 enumerate(row)
    #             ]
    #             for y, row in
    #             enumerate(state)
    #         ]
    #     )

    def __iter__(self) -> t.Iterator[CardStacker]:
        return self.stackers

    def __str__(self):
        return '[\n' + '\n'.join(
            '\t[' + ', '.join(
                str(cell.position)
                for cell in
                row
            ) + ']'
            for row in
            zip(*self._grid)
        ) + '\n]'


class StackingGrid(Aligner):

    def __init__(self, scene: SelectionScene, *, margin: float = .2):
        super().__init__(scene)

        self._stacked_cards: t.Dict[PhysicalCard, _CardInfo] = {}

        self._margin_pixel_size = margin * IMAGE_WIDTH

        self._stacker_map = self.create_stacker_map()

        # self._cursor_position: t.Optional[PhysicalCard] = None
        # self._cursor_index = 0

    @classmethod
    def _inflate(
        cls,
        margin: float,
        stacker_map: StackerMap,
        stacked_cards: t.Dict[PhysicalCard, _CardInfo],
    ) -> StackingGrid:
        stacking_grid = cls.__new__(cls)

        stacking_grid._stacked_cards = stacked_cards
        stacking_grid._margin_pixel_size = margin
        stacking_grid._stacker_map = stacker_map

        return stacking_grid

    def __reduce__(self):
        return self._inflate, (self._margin_pixel_size, self._stacker_map, self._stacked_cards)

    @abstractmethod
    def create_stacker_map(self) -> StackerMap:
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

    # @property
    # def cursor_position(self) -> t.Optional[PhysicalCard]:
    #     return self._cursor_position

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

    # def link_cursor(self, card: t.Optional[PhysicalCard]) -> None:
    #     if card is None:
    #         self._cursor_position = None
    #         self._scene.cursor.setPos(0, 0)
    #         self.cursor_moved.emit(QtCore.QPointF(0, 0))
    #         return
    #
    #     self._cursor_position = card
    #     self._scene.cursor.setPos(card.pos())
    #     self.cursor_moved.emit(self._cursor_position.pos())

    # def find_stacker(self, x: int, y: int, direction: Direction) -> t.Optional[CardStacker]:
    #
    #     if not self._stacked_cards:
    #         return None
    #
    #     x, y = int(x), int(y)
    #
    #     if direction == Direction.UP:
    #         for _x in chain(
    #             range(x, self.stacker_map.row_length),
    #             reversed(range(0, x)),
    #         ):
    #             for _y in reversed(range(0, y + 1)):
    #                 if _x == x and _y == y:
    #                     continue
    #                 stacker = self.get_card_stacker_at_index(_x, _y)
    #                 if stacker.cards:
    #                     return stacker
    #
    #         for _x in chain(
    #             range(x, self.stacker_map.row_length),
    #             reversed(range(0, x)),
    #         ):
    #             for _y in reversed(range(y + 1, self.stacker_map.column_height)):
    #                 if _x == x and _y == y:
    #                     continue
    #                 stacker = self.get_card_stacker_at_index(_x, _y)
    #                 if stacker.cards:
    #                     return stacker
    #
    #     elif direction == Direction.RIGHT:
    #         for _y in chain(
    #             range(y, self.stacker_map.column_height),
    #             reversed(range(0, y)),
    #         ):
    #             for _x in range(x, self.stacker_map.row_length):
    #                 if _x == x and _y == y:
    #                     continue
    #                 stacker = self.get_card_stacker_at_index(_x, _y)
    #                 if stacker.cards:
    #                     return stacker
    #
    #         for _y in chain(
    #             range(y, self.stacker_map.column_height),
    #             reversed(range(0, y)),
    #         ):
    #             for _x in range(0, x):
    #                 if _x == x and _y == y:
    #                     continue
    #                 stacker = self.get_card_stacker_at_index(_x, _y)
    #                 if stacker.cards:
    #                     return stacker
    #
    #     elif direction == Direction.DOWN:
    #         for _x in chain(
    #             reversed(range(0, x + 1)),
    #             range(x + 1, self.stacker_map.row_length),
    #         ):
    #             for _y in range(y + 1, self.stacker_map.column_height):
    #                 if _x == x and _y == y:
    #                     continue
    #                 stacker = self.get_card_stacker_at_index(_x, _y)
    #                 if stacker.cards:
    #                     return stacker
    #
    #         for _x in chain(
    #             reversed(range(0, x + 1)),
    #             range(x + 1, self.stacker_map.row_length),
    #         ):
    #             for _y in range(0, y + 1):
    #                 if _x == x and _y == y:
    #                     continue
    #                 stacker = self.get_card_stacker_at_index(_x, _y)
    #                 if stacker.cards:
    #                     return stacker
    #
    #     elif direction == Direction.LEFT:
    #         for _y in chain(
    #             reversed(range(0, y + 1)),
    #             range(y + 1, self.stacker_map.column_height),
    #         ):
    #             for _x in reversed(range(0, x + 1)):
    #                 if _x == x and _y == y:
    #                     continue
    #                 stacker = self.get_card_stacker_at_index(_x, _y)
    #                 if stacker.cards:
    #                     return stacker
    #
    #         for _y in chain(
    #             reversed(range(0, y + 1)),
    #             range(y + 1, self.stacker_map.column_height),
    #         ):
    #             for _x in reversed(range(x + 1, self.stacker_map.row_length)):
    #                 if _x == x and _y == y:
    #                     continue
    #                 stacker = self.get_card_stacker_at_index(_x, _y)
    #                 if stacker.cards:
    #                     return stacker

    # def find_stacker_spiraled(self, x: int, y: int, direction: Direction) -> t.Optional[CardStacker]:
    # 	if not self._stacked_cards:
    # 		return None
    #
    # 	x, y = int(x), int(y)
    #
    # 	_iter = spiral(direction)
    #
    # 	for dx, dy in (
    # 		next(_iter)
    # 		for _ in
    # 		range(
    # 			self.stacker_map.row_length
    # 			* self.stacker_map.column_height
    # 			* 4
    # 		)
    # 	):
    # 		stacker = self.get_card_stacker_at_index(x + dx, y + dy)
    #
    # 		if stacker.cards:
    # 			return stacker
    #
    # 	return None

    def _move_cards(self, cards: t.List[PhysicalCard], stacker: CardStacker):
        if not cards:
            return

        # self._undo_stack.push(
        #     _StackingMove(
        #         self,
        #         self._scene.selectedItems(),
        #         stacker,
        #     )
        # )
        #
        # self.link_cursor(cards[-1])

    # def move_cursor(self, direction: Direction, modifiers: int = 0):
    #     if self._cursor_position is None:
    #         return
    #
    #     info = self._stacked_cards[self.cursor_position]
    #
    #     if modifiers & QtCore.Qt.ShiftModifier:
    #         selected_items = self._scene.selectedItems()
    #
    #         if modifiers & QtCore.Qt.ControlModifier:
    #             stacker = self.find_stacker(*info.card_stacker.index, direction = direction)
    #
    #             if stacker is None:
    #                 return
    #
    #         else:
    #
    #             stacker = self.get_card_stacker_at_index(
    #                 info.card_stacker.index[0] + direction.value[0],
    #                 info.card_stacker.index[1] + direction.value[1],
    #             )
    #
    #         self._move_cards(selected_items, stacker)
    #         return
    #
    #     if direction == Direction.UP:
    #         stacker = info.card_stacker
    #         position = info.position - 1
    #
    #         if position < 0:
    #             next_stacker = self.find_stacker(*stacker.index, direction = direction)
    #
    #             if next_stacker is not None:
    #                 stacker = next_stacker
    #
    #         # self.link_cursor(stacker.cards[position])
    #         self._cursor_index = position
    #
    #     elif direction == Direction.DOWN:
    #         stacker = info.card_stacker
    #         position = info.position + 1
    #
    #         if position >= len(stacker.cards):
    #             next_stacker = self.find_stacker(*stacker.index, direction = direction)
    #
    #             if next_stacker is not None:
    #                 stacker = next_stacker
    #
    #             position = 0
    #
    #         # self.link_cursor(stacker.cards[position])
    #         self._cursor_index = position

        # else:
        #     stacker = info.card_stacker
        #
        #     next_stacker = self.find_stacker(*stacker.index, direction = direction)
        #
        #     if next_stacker is not None:
        #         stacker = next_stacker

        # self.link_cursor(
        #     stacker.cards[
        #         min(
        #             len(stacker.cards) - 1,
        #             max(
        #                 info.position,
        #                 self._cursor_index,
        #             )
        #         )
        #     ]
        # )

        # if modifiers & QtCore.Qt.ControlModifier:
        #     self._scene.add_selection((self._cursor_position,))
        #
        # elif modifiers & QtCore.Qt.AltModifier:
        #     self._scene.remove_selected((self._cursor_position,))
        #
        # else:
        #     self._scene.set_selection((self._cursor_position,))
        #
        # Context.card_view.set_image.emit(self._cursor_position.image_request())

    # @abstractmethod
    # def _can_create_rows(self, amount: int) -> bool:
    # 	pass
    #
    # @abstractmethod
    # def _can_create_columns(self, amount: int) -> bool:
    # 	pass
    #
    # @abstractmethod
    # def _create_rows(self, amount: int) -> None:
    # 	pass
    #
    # @abstractmethod
    # def _create_columns(self, amount: int) -> None:
    # 	pass

    def get_card_stacker_at_index(self, x: int, y: int) -> CardStacker:
        x_index = min(max(x, 0), self.stacker_map.row_length - 1)
        y_index = min(max(y, 0), self.stacker_map.column_height - 1)

        # required_columns = x - self._stacker_map.row_length + 1
        # required_rows = y - self._stacker_map.column_height + 1
        #
        # if (
        # 	( required_rows > 0 or required_columns > 0 )
        # 	and self._can_create_rows(required_rows)
        # 	and self._can_create_columns(required_columns)
        # ):
        # 	if required_rows > 0:
        # 		self._create_rows(required_rows)
        # 	if required_columns > 0:
        # 		self._create_columns(required_columns)
        #
        # else:
        # 	x = min(x, self.stacker_map.row_length - 1)
        # 	y = min(y, self.stacker_map.column_height - 1)

        return self.stacker_map.get_stacker(x_index, y_index)

    def get_card_stacker(self, x: int, y: int) -> CardStacker:
        return self.get_card_stacker_at_index(
            *self._stacker_map.map_position_to_index(x, y)
        )

    SORT_PROPERTY_MAP: t.Mapping[t.Type[sorting.SortProperty], t.Type[_StackingSort]] = {
        sorting.ColorExtractor: ColorSort,
        sorting.ColorIdentityExtractor: ColorIdentitySort,
        sorting.CMCExtractor: CmcSort,
        sorting.NameExtractor: NameSort,
        sorting.IsLandExtractor: IsLandSplit,
        sorting.IsCreatureExtractor: IsCreatureSplit,
        sorting.CubeableTypeExtractor: CubeableTypeSort,
        sorting.IsMonoExtractor: IsMonoSplit,
        sorting.RarityExtractor: RaritySort,
        sorting.ExpansionExtractor: ExpansionSort,
        sorting.CollectorNumberExtractor: CollectorsNumberSort,
    }

    def sort(
        self,
        sort_property: t.Type[sorting.SortProperty],
        cards: t.Sequence[PhysicalCard],
        orientation: int,
        in_place: bool = False,
    ) -> QUndoCommand:
        return self.SORT_PROPERTY_MAP[sort_property](self, cards, orientation, in_place)

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
                    stacker,
                    sort_property,
                )
            )

        return _sort_stack

    def context_menu(self, menu: QtWidgets.QMenu, position: QPoint, undo_stack: QUndoStack) -> None:
        stacker = self.get_card_stacker(position.x(), position.y())

        stacker_sort_menu = menu.addMenu('Sort Stack')

        for sort_property in sorting.SortProperty.names_to_sort_property.values():
            sort_action = QtWidgets.QAction(sort_property.name, stacker_sort_menu)
            sort_action.triggered.connect(self._get_sort_stack(stacker, sort_property, undo_stack))
            stacker_sort_menu.addAction(sort_action)

    # def persist(self) -> t.Any:
    #     return {
    #         'stacker_map': self._stacker_map.persist(),
    #     }
    #
    # @classmethod
    # def load(cls, state: t.Any) -> StackingGrid:
    #     pass
