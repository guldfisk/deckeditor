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
    def value(self):
        return Context.settings.value(self._key, self._default_value, self.setting_type)

    @property
    def default_value(self) -> t.Any:
        return self._default_value

    @property
    def requires_restart(self) -> bool:
        return self._requires_restart

    def reset(self) -> None:
        pass

    def render(self, layout: QtWidgets.QFormLayout) -> None:
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

        self._box.stateChanged.connect(lambda v: self.selected.emit(self, v == 2))
        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def reset(self) -> None:
        self._box.setChecked(self.value)

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._box)


class StringSetting(Setting):
    setting_type = str

    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        default_value: str,
        requires_restart: bool = False,
        *,
        hide_text: bool = False,
    ):
        super().__init__(key, name, description, default_value, requires_restart = requires_restart)

        self._label = HoverLabel(self._name, self._description)
        self._field = QtWidgets.QLineEdit()

        if hide_text:
            self._field.setEchoMode(QtWidgets.QLineEdit.Password)

        self._field.editingFinished.connect(lambda: self.selected.emit(self, self._field.text()))

        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def reset(self) -> None:
        self._field.setText(self.value)

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._field)


class OptionsSetting(Setting):
    setting_type = str

    def __init__(
        self,
        key: str,
        name: str,
        description: str,
        default_value: str,
        options: t.Sequence[str],
        requires_restart: bool = False,
    ):
        super().__init__(key, name, description, default_value, requires_restart = requires_restart)

        self._label = HoverLabel(self._name, self._description)
        self._combo = QtWidgets.QComboBox()

        self._combo.addItems(options)

        self._combo.currentTextChanged.connect(lambda v: self.selected.emit(self, v))
        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def reset(self) -> None:
        self._combo.setCurrentText(self.value)

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._combo)
