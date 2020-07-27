import typing as t
from dataclasses import dataclass

from PyQt5 import QtCore

from magiccube.collections.cubeable import Cubeable


@dataclass
class CubeableFocusEvent(object):
    cubeable: Cubeable
    size: t.Optional[t.Tuple[float, float]] = None
    position: t.Optional[t.Tuple[float, float]] = None
    modifiers: t.Optional[QtCore.Qt.KeyboardModifiers] = None
    back: bool = False


# class CubeableFocusEvent(object):
#
#     def __init__(
#         self,
#         cubeable: Cubeable,
#         size: t.Optional[t.Tuple[float, float]] = None,
#         position: t.Optional[t.Tuple[float, float]] = None,
#         modifiers: t.Optional[QtCore.Qt.KeyboardModifiers] = None,
#         back: bool = False,
#     ):
#         self._cubeable = cubeable
#         self._size = size
#         self._position = position
#         self._modifiers = modifiers
#         self._back = back
#
#     @property
#     def cubeable(self) -> Cubeable:
#         return self._cubeable
#
#     @property
#     def size(self) -> t.Optional[t.Tuple[float, float]]:
#         return self._size
#
#     @property
#     def position(self) -> t.Optional[t.Tuple[float, float]]:
#         return self._position
#
#     @property
#     def modifiers(self) -> QtCore.Qt.KeyboardModifier:
#         return self._modifiers
#
#     @property
#     def (self):
#         return
