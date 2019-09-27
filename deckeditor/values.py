from enum import Enum


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
