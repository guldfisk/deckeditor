from enum import Enum

from mtgimg.interface import IMAGE_SIZE_MAP, SizeSlug


class DeckZoneType(Enum):
    MAINDECK = 'Maindeck'
    SIDEBOARD = 'Sideboard'
    POOL = 'Pool'


class SortProperty(Enum):
    NAME = 'Name'
    CMC = 'Cmc'
    RARITY = 'Rarity'
    COLOR = 'Color'
    TYPE = 'Type'
    EXPANSION = 'Expansion'
    COLLECTOR_NUMBER = 'Collector Number'


class Direction(Enum):
    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)


IMAGE_WIDTH, IMAGE_HEIGHT = IMAGE_SIZE_MAP[frozenset((SizeSlug.ORIGINAL, False))]