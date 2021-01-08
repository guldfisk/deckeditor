import typing as t
from dataclasses import dataclass

from PyQt5 import QtCore

from mtgorp.models.interfaces import Cardboard

from magiccube.collections.cubeable import Cubeable


Focusable = t.Union[Cubeable, Cardboard]


@dataclass
class FocusEvent(object):
    focusable: Focusable
    size: t.Optional[t.Tuple[float, float]] = None
    position: t.Optional[t.Tuple[float, float]] = None
    modifiers: t.Optional[QtCore.Qt.KeyboardModifiers] = None
    back: bool = False
    release_id: t.Optional[int] = None
