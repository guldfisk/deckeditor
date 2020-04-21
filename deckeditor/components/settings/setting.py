from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QObject

from deckeditor.context.context import Context


class HoverLabel(QtWidgets.QLabel):
    focus_description = pyqtSignal(str)

    def __init__(self, text: str, description: str):
        super().__init__(text)
        self._description = description

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self.focus_description.emit(self._description)


class Setting(QObject):
    selected = pyqtSignal(object, object)
    show_description = pyqtSignal(object, str)
    setting_type = t.Type

    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        default_value: t.Any,
        requires_restart: bool = False,
    ):
        super().__init__()
        self._key = key
        self._name = name
        self._description = description
        self._default_value = default_value
        self._requires_restart = requires_restart

    @property
    def key(self) -> str:
        return self._key

    @property
    def default_value(self) -> t.Any:
        return self._default_value

    @property
    def requires_restart(self) -> bool:
        return self._requires_restart

    def render(self, layout: QtWidgets.QLayout):
        pass


class BooleanSetting(Setting):
    setting_type = bool

    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        default_value: bool,
        requires_restart: bool = False,
    ):
        super().__init__(key, name, description, default_value, requires_restart = requires_restart)

        self._label = HoverLabel(self._name, self._description)
        self._box = QtWidgets.QCheckBox()
        self._box.setChecked(Context.settings.value(self._key, self._default_value, bool))

        self._box.stateChanged.connect(lambda v: self.selected.emit(self, v == 2))
        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def render(self, layout: QtWidgets.QVBoxLayout):
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self._label)
        row.addWidget(self._box)
        layout.addLayout(row)
