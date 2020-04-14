import typing as t

from PyQt5 import QtCore

from magiccube.collections.cubeable import Cubeable


class CubeableFocusEvent(object):

    def __init__(
        self,
        cubeable: Cubeable,
        size: t.Optional[t.Tuple[float, float]] = None,
        position: t.Optional[t.Tuple[float, float]] = None,
        modifiers: t.Optional[QtCore.Qt.KeyboardModifiers] = None,
    ):
        self._cubeable = cubeable
        self._size = size
        self._position = position
        self._modifiers = modifiers

    @property
    def cubeable(self) -> Cubeable:
        return self._cubeable

    @property
    def size(self) -> t.Optional[t.Tuple[float, float]]:
        return self._size

    @property
    def position(self) -> t.Optional[t.Tuple[float, float]]:
        return self._position

    @property
    def modifiers(self) -> QtCore.Qt.KeyboardModifier:
        return self._modifiers
