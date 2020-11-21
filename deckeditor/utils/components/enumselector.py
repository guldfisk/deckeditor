import typing as t
from enum import Enum

from PyQt5 import QtWidgets


T = t.TypeVar('T', bound = Enum)


class EnumSelector(t.Generic[T], QtWidgets.QComboBox):

    def __init__(self, enum_type: t.Type[T]):
        super().__init__()
        self._enum_type = enum_type
        self.addItems(
            d.value
            for d in
            enum_type
        )
        self.setCurrentText(enum_type.__iter__().__next__().value)

    def set_value(self, value: T) -> None:
        self.setCurrentText(value.value)

    def get_value(self) -> T:
        return self._enum_type(self.currentText())
