from __future__ import annotations

import collections
import datetime
import functools
import itertools
import typing as t
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum

from mtgorp.models.persistent.attributes import typeline, colors
from mtgorp.models.interfaces import Printing

from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap, IntentionType

from deckeditor.context.context import Context
from deckeditor.models.cubes.scenecard import SceneCard


SortValue = t.Union[str, int, datetime.datetime]


class DimensionContinuity(Enum):
    AUTO = 'auto'
    CONTINUOUS = 'continuous'
    GROUPED = 'grouped'

    def continuity_for(self, sort_property: t.Type[SortProperty]) -> DimensionContinuity:
        if self == self.AUTO:
            return sort_property.auto_continuity
        return self


class SortDirection(Enum):
    AUTO = 'auto'
    ASCENDING = 'asc'
    DESCENDING = 'desc'

    def direction_for(self, sort_property: t.Type[SortProperty]) -> bool:
        if self == self.AUTO:
            return sort_property.auto_reverse
        return self == self.DESCENDING


@functools.total_ordering
class SortDimension(Enum):
    AUTO = 'auto'
    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'
    SUB_DIVISIONS = 'sub divisions'

    def dimension_for(self, sort_property: t.Type[SortProperty]) -> SortDimension:
        if self == self.AUTO:
            return sort_property.auto_dimension
        return self

    def __lt__(self, other):
        return DIMENSION_ORDER_MAP[self] < DIMENSION_ORDER_MAP[other]


DIMENSION_ORDER_MAP = {
    dimension: idx
    for idx, dimension in
    enumerate(SortDimension)
}


class _SortPropertyMeta(ABCMeta):
    names_to_sort_property: t.MutableMapping[str, t.Type[SortProperty]] = OrderedDict()

    def __new__(mcs, classname, base_classes, attributes):
        klass = type.__new__(mcs, classname, base_classes, attributes)

        if 'name' in attributes and attributes['name'] is not None:
            mcs.names_to_sort_property[attributes['name']] = klass

        return klass


class SortProperty(object, metaclass = _SortPropertyMeta):
    name: str = None
    auto_dimension: SortDimension = SortDimension.HORIZONTAL
    auto_reverse: bool = False
    auto_continuity: DimensionContinuity = DimensionContinuity.GROUPED

    @classmethod
    @abstractmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> SortValue:
        pass


@dataclass
class SortSpecification(object):
    sort_property: t.Type[SortProperty]
    index: int = 0
    dimension: SortDimension = SortDimension.AUTO
    direction: SortDirection = SortDirection.AUTO
    respect_custom: bool = True
    macro: SortMacro = None

    def __repr__(self) -> str:
        return '{}({}, {}, {}, {}, {})'.format(
            self.__class__.__name__,
            self.index,
            self.sort_property.name,
            self.dimension.value,
            self.direction.value,
            self.respect_custom,
        )


@dataclass
class SortMacro(object):
    specifications: t.Sequence[SortSpecification]
    index: int = 0
    name: str = ''
    horizontal_continuity: DimensionContinuity = DimensionContinuity.AUTO
    vertical_continuity: DimensionContinuity = DimensionContinuity.AUTO
    sub_continuity: DimensionContinuity = DimensionContinuity.AUTO

    def continuity_for_dimension(self, dimension: SortDimension) -> DimensionContinuity:
        if dimension == SortDimension.HORIZONTAL:
            return self.horizontal_continuity
        if dimension == SortDimension.VERTICAL:
            return self.vertical_continuity
        return self.sub_continuity

    @property
    def dimension_specifications_map(self) -> t.Sequence[t.Tuple[SortDimension, t.Sequence[SortSpecification]]]:
        _map = collections.defaultdict(list)
        for specification in self.specifications:
            _map[specification.dimension.dimension_for(specification.sort_property)].append(specification)

        return sorted(
            (
                (dimension, sorted(specifications, key = lambda s: s.index))
                for dimension, specifications in
                _map.items()
            ),
            key = lambda p: p[0],
        )

    def __repr__(self) -> str:
        return '{}({}, {})'.format(
            self.__class__.__name__,
            self.name,
            self.index,
        )


@functools.total_ordering
class SortIdentity(object):

    def __init__(self, values: t.Tuple[t.Type[SortValue, bool], ...]):
        self._values = values

    @property
    def values(self) -> t.Tuple[t.Type[SortValue, bool], ...]:
        return self._values

    @classmethod
    def for_card(cls, card: SceneCard, specifications: t.Sequence[SortSpecification]) -> SortIdentity:
        return cls(
            tuple(
                (
                    specification.sort_property.extract(card, respect_custom = specification.respect_custom),
                    specification.direction.direction_for(specification.sort_property),
                )
                for specification in
                specifications
            )
        )

    def __hash__(self) -> int:
        return hash(self._values)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._values == other._values
        )

    def __lt__(self, other) -> bool:
        for s, o in itertools.zip_longest(self._values, other.values):
            if s is None:
                return True
            if o is None:
                return False
            if s[0] < o[0]:
                return not s[1]
            if s[0] > o[0]:
                return s[1]
        return False

    def __repr__(self) -> str:
        return '{}({})'.format(
            self.__class__.__name__,
            self._values,
        )


class ColorExtractor(SortProperty):
    name = 'Color'

    @classmethod
    def extract_color(cls, cubeable: Printing, *, respect_custom: bool = True):
        if not respect_custom:
            return cubeable.cardboard.front_card.color
        return Context.sort_map.get_cardboard_value(cubeable.cardboard, 'colors', cubeable.cardboard.front_card.color)

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if not isinstance(card.cubeable, Printing):
            return -2
        if typeline.LAND in card.cubeable.cardboard.front_card.type_line:
            return -1
        return colors.color_set_sort_value_len_first(
            cls.extract_color(card.cubeable, respect_custom = respect_custom)
        )


class ColorIdentityExtractor(SortProperty):
    name = 'Color Identity'

    @classmethod
    def extract_color_identity(cls, cubeable: Printing, *, respect_custom: bool = True):
        if not respect_custom:
            return cubeable.cardboard.front_card.color_identity
        return Context.sort_map.get_cardboard_value(
            cubeable.cardboard,
            'color_identity',
            cubeable.cardboard.front_card.color_identity,
        )

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if not isinstance(card.cubeable, Printing):
            return -1
        return colors.color_set_sort_value_len_first(
            cls.extract_color_identity(card.cubeable)
        )


class CMCExtractor(SortProperty):
    name = 'Cmc'

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if not isinstance(card.cubeable, Printing):
            return -2
        if respect_custom:
            custom_cmc = Context.sort_map.get_cardboard_value(card.cubeable.cardboard, 'cmc')
            if custom_cmc is not None:
                return custom_cmc
        if typeline.LAND in card.cubeable.cardboard.front_card.type_line:
            return -1
        return card.cubeable.cardboard.front_card.cmc


class NameExtractor(SortProperty):
    name = 'Name'
    auto_continuity = DimensionContinuity.CONTINUOUS

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> str:
        if not isinstance(card.cubeable, Printing):
            return ''
        return card.cubeable.cardboard.front_card.name


class IsLandExtractor(SortProperty):
    name = 'Land Split'
    auto_dimension = SortDimension.VERTICAL

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if not isinstance(card.cubeable, Printing):
            return -1
        return int(typeline.LAND in card.cubeable.cardboard.front_card.type_line)


class IsPermanentSplit(SortProperty):
    name = 'Permanent Split'
    auto_dimension = SortDimension.VERTICAL

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if not isinstance(card.cubeable, Printing):
            return -1
        return int(card.cubeable.cardboard.front_card.type_line.is_permanent)


class IsCreatureExtractor(SortProperty):
    name = 'Creature Split'
    auto_dimension = SortDimension.VERTICAL

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if not isinstance(card.cubeable, Printing):
            return -1
        return int(typeline.CREATURE in card.cubeable.cardboard.front_card.type_line)


class CubeableTypeExtractor(SortProperty):
    name = 'Cubeable Type'

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if isinstance(card.cubeable, Printing):
            return 0
        if isinstance(card.cubeable, Trap):
            if card.cubeable.intention_type != IntentionType.SYNERGY:
                return 1
            return 2
        if isinstance(card.cubeable, Ticket):
            return 3
        return 4


class IsMonoExtractor(SortProperty):
    name = 'Mono Split'
    auto_dimension = SortDimension.VERTICAL

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if not isinstance(card.cubeable, Printing):
            return -1
        return int(len(card.cubeable.cardboard.front_card.color) == 1)


class RarityExtractor(SortProperty):
    name = 'Rarity'

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        if not isinstance(card.cubeable, Printing):
            return -2
        return -1 if card.cubeable.rarity is None else card.cubeable.rarity.value


class ReleaseDateExtractor(SortProperty):
    name = 'Release Date'
    auto_continuity = DimensionContinuity.CONTINUOUS

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> datetime.datetime:
        return (
            datetime.datetime.fromtimestamp(0)
            if not isinstance(card.cubeable, Printing) or card.cubeable.expansion is None else
            card.cubeable.expansion.release_date
        )


class ExpansionExtractor(SortProperty):
    name = 'Expansion'

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> str:
        return (
            ''
            if not isinstance(card.cubeable, Printing) or card.cubeable.expansion is None else
            card.cubeable.expansion.code
        )


class CollectorNumberExtractor(SortProperty):
    name = 'Collector Number'
    auto_continuity = DimensionContinuity.CONTINUOUS

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        return (
            card.cubeable.collector_number
            if isinstance(card.cubeable, Printing) else
            -1
        )


class RatingExtractor(SortProperty):
    name = 'Rating'
    auto_continuity = DimensionContinuity.CONTINUOUS
    auto_reverse = True

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        return card.values.get('rating', 0)


class IsGhost(SortProperty):
    name = 'Is Ghost'
    auto_dimension = SortDimension.VERTICAL

    @classmethod
    def extract(cls, card: SceneCard, *, respect_custom: bool = True) -> int:
        return int(card.values.get('ghost', 0))
