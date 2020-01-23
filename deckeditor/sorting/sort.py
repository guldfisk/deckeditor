import  typing as t

from enum import Enum

from magiccube.laps.lap import Lap
from mtgorp.models.persistent.attributes import typeline, colors

from magiccube.collections import cubeable as Cubeable
from mtgorp.models.persistent.printing import Printing


class SortProperty(Enum):
    NAME = 'Name'
    COLOR = 'Color'
    Color_IDENTIRY = 'Color Identity'
    CMC = 'Cmc'
    RARITY = 'Rarity'
    TYPE = 'Type'
    EXPANSION = 'Expansion'
    COLLECTOR_NUMBER = 'Collector Number'


def extract_name(cubeable: Cubeable) -> str:
    if not isinstance(cubeable, Printing):
        return ''
    return cubeable.cardboard.front_card.name


def extract_cmc(cubeable: Cubeable) -> int:
    if not isinstance(cubeable, Printing):
        return -2
    if typeline.LAND in cubeable.cardboard.front_card.type_line:
        return -1
    return cubeable.cardboard.front_card.cmc


def extract_rarity(cubeable: Cubeable) -> int:
    if not isinstance(cubeable, Printing):
        return -2
    return -1 if cubeable.rarity is None else cubeable.rarity.value


def extract_color(cubeable: Cubeable) -> int:
    if not isinstance(cubeable, Printing):
        return -2
    if typeline.LAND in cubeable.cardboard.front_card.type_line:
        return -1
    return colors.color_set_sort_value_len_first(
        cubeable.cardboard.front_card.color
    )

def extract_color_identity(cubeable: Cubeable) -> int:
    if not isinstance(cubeable, Printing):
        return -1
    return colors.color_set_sort_value_len_first(
        cubeable.cardboard.front_card.color_identity
    )


def extract_type(cubeable: Cubeable) -> int:
    if not isinstance(cubeable, Printing):
        return -1
    return int(typeline.CREATURE in cubeable.cardboard.front_card.type_line)


def extract_expansion(cubeable: Cubeable) -> str:
    return (
        ''
        if not isinstance(cubeable, Printing) or cubeable.expansion is None else
        cubeable.expansion.code
    )


def extract_collector_number(cubeable: Cubeable) -> int:
    return (
        cubeable.collector_number
        if isinstance(cubeable, Printing) else
        -1
    )


EXTRACTOR_MAP: t.Mapping[SortProperty, t.Callable[[t.Union[Printing, Lap]], t.Union[str, int]]] = {
    SortProperty.NAME: extract_name,
    SortProperty.CMC: extract_cmc,
    SortProperty.COLOR: extract_color,
    SortProperty.Color_IDENTIRY: extract_color_identity,
    SortProperty.RARITY: extract_rarity,
    SortProperty.TYPE: extract_type,
    SortProperty.EXPANSION: extract_expansion,
    SortProperty.COLLECTOR_NUMBER: extract_collector_number,
}


def extract_sort_value(cubeable: Cubeable, sort_property: SortProperty) -> t.Union[str, int]:
    return EXTRACTOR_MAP[sort_property](cubeable)
