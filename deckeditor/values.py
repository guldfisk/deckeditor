from __future__ import annotations

import logging
import sys
from enum import Enum

from mtgimg.interface import IMAGE_SIZE_MAP, SizeSlug


APPLICATION_NAME = 'Embargo Edit'
VERSION = '0.1.2'

IS_WINDOWS = sys.platform.startswith('win')

EXECUTE_PATH = (
    ''
    if IS_WINDOWS else
    '/usr/share/embargoedit/editor/editor'
)

STANDARD_DATETIME_FORMAT = '%d-%m-%Y %H:%M'


class DeckZoneType(Enum):
    MAINDECK = 'Maindeck'
    SIDEBOARD = 'Sideboard'
    POOL = 'Pool'


class Direction(Enum):
    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)


IMAGE_WIDTH, IMAGE_HEIGHT = IMAGE_SIZE_MAP[frozenset((SizeSlug.MEDIUM, False))]

STANDARD_IMAGE_MARGIN = .1

SUPPORTED_EXTENSIONS = '*.deck *.cod *.json *.dec *.mwDeck *.embd *.embp'

LOGGING_LEVEL_MAP = {
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
}
