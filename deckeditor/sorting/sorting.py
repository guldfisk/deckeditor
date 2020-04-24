from __future__ import annotations

import typing as t

from abc import ABCMeta, abstractmethod
from collections import OrderedDict

from PyQt5 import QtCore

from mtgorp.models.persistent.attributes import typeline, colors
from mtgorp.models.persistent.printing import Printing

from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap
from magiccube.collections.cubeable import Cubeable

from deckeditor.context.context import Context


class _SortPropertyMeta(ABCMeta):

    names_to_sort_property: t.MutableMapping[str, t.Type[SortProperty]] = OrderedDict()

    def __new__(mcs, classname, base_classes, attributes):
        klass = type.__new__(mcs, classname, base_classes, attributes)

        if 'name' in attributes and attributes['name'] is not None:
            mcs.names_to_sort_property[attributes['name']] = klass

        return klass


class SortProperty(object, metaclass = _SortPropertyMeta):
    name: str = None
    auto_direction: QtCore.Qt.Orientation = QtCore.Qt.Horizontal

    @classmethod
    @abstractmethod
    def extract(cls, cubeable: Cubeable) -> t.Union[str, int]:
        pass


class ColorExtractor(SortProperty):
    name = 'Color'

    @classmethod
    def extract_color(cls, cubeable: Printing):
        return Context.sort_map.get_cardboard_value(cubeable.cardboard, 'colors', cubeable.cardboard.front_card.color)

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        if not isinstance(cubeable, Printing):
            return -2
        if typeline.LAND in cubeable.cardboard.front_card.type_line:
            return -1
        return colors.color_set_sort_value_len_first(
            cls.extract_color(cubeable)
        )


class ColorIdentityExtractor(SortProperty):
    name = 'Color Identity'

    @classmethod
    def extract_color_identity(cls, cubeable: Printing):
        return Context.sort_map.get_cardboard_value(
            cubeable.cardboard,
            'color_identity',
            cubeable.cardboard.front_card.color_identity,
        )

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        if not isinstance(cubeable, Printing):
            return -1
        return colors.color_set_sort_value_len_first(
            cls.extract_color_identity(cubeable)
        )


class CMCExtractor(SortProperty):
    name = 'Cmc'

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        if not isinstance(cubeable, Printing):
            return -2
        custom_cmc = Context.sort_map.get_cardboard_value(cubeable.cardboard, 'cmc')
        if custom_cmc is not None:
            return custom_cmc
        if typeline.LAND in cubeable.cardboard.front_card.type_line:
            return -1
        return cubeable.cardboard.front_card.cmc


class NameExtractor(SortProperty):
    name = 'Name'

    @classmethod
    def extract(cls, cubeable: Cubeable) -> str:
        if not isinstance(cubeable, Printing):
            return ''
        return cubeable.cardboard.front_card.name


class IsLandExtractor(SortProperty):
    name = 'Land Split'
    auto_direction = QtCore.Qt.Vertical

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        if not isinstance(cubeable, Printing):
            return -1
        return int(typeline.LAND in cubeable.cardboard.front_card.type_line)


class IsCreatureExtractor(SortProperty):
    name = 'Creature Split'
    auto_direction = QtCore.Qt.Vertical

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        if not isinstance(cubeable, Printing):
            return -1
        return int(typeline.CREATURE in cubeable.cardboard.front_card.type_line)


class CubeableTypeExtractor(SortProperty):
    name = 'Cubeable Type'

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        if isinstance(cubeable, Printing):
            return 0
        if isinstance(cubeable, Trap):
            if cubeable.intention_type != Trap.IntentionType.SYNERGY:
                return 1
            return 2
        if isinstance(cubeable, Ticket):
            return 3
        return 4


class IsMonoExtractor(SortProperty):
    name = 'Mono Split'
    auto_direction = QtCore.Qt.Vertical

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        if not isinstance(cubeable, Printing):
            return -1
        return int(len(cubeable.cardboard.front_card.color) == 1)


class RarityExtractor(SortProperty):
    name = 'Rarity'

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        if not isinstance(cubeable, Printing):
            return -2
        return -1 if cubeable.rarity is None else cubeable.rarity.value


class ExpansionExtractor(SortProperty):
    name = 'Expansion'

    @classmethod
    def extract(cls, cubeable: Cubeable) -> str:
        return (
            ''
            if not isinstance(cubeable, Printing) or cubeable.expansion is None else
            cubeable.expansion.code
        )


class CollectorNumberExtractor(SortProperty):
    name = 'Collector Number'

    @classmethod
    def extract(cls, cubeable: Cubeable) -> int:
        return (
            cubeable.collector_number
            if isinstance(cubeable, Printing) else
            -1
        )
