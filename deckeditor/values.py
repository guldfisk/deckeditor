import sys
from enum import Enum

from mtgimg.interface import IMAGE_SIZE_MAP, SizeSlug


APPLICATION_NAME = 'Embargo Edit'
VERSION = '0.0.1'

IS_WINDOWS = sys.platform.startswith('win')

EXECUTE_PATH = (
    ''
    if IS_WINDOWS else
    '/usr/share/embargoedit/editor/editor'
)


class DeckZoneType(Enum):
    MAINDECK = 'Maindeck'
    SIDEBOARD = 'Sideboard'
    POOL = 'Pool'


class Direction(Enum):
    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)


class SortDirection(Enum):
    ASCENDING = 'asc'
    DESCENDING = 'desc'
    AUTO = 'auto'


class SortDimension(Enum):
    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'
    SUB_DIVISIONS = 'sub divisions'
    AUTO = 'auto'


IMAGE_WIDTH, IMAGE_HEIGHT = IMAGE_SIZE_MAP[frozenset((SizeSlug.MEDIUM, False))]

STANDARD_IMAGE_MARGIN = .1

SUPPORTED_EXTENSIONS = '*.deck *.cod *.json *.dec *.mwDeck *.embd *.embp'
