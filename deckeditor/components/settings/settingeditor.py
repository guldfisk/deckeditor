from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QObject

from sqlalchemy.orm.attributes import QueryableAttribute

from deckeditor.components.settings.settings import Setting
from deckeditor.store import EDB


class HoverLabel(QtWidgets.QLabel):
    focus_description = pyqtSignal(str)

    def __init__(self, text: str, description: str):
        super().__init__(text)
        self._description = description

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self.focus_description.emit(self._description)


class SettingEditor(QObject):
    selected = pyqtSignal(object, object)
    show_description = pyqtSignal(object, str)
    setting_type: t.Type

    def __init__(
        self,
        setting: Setting,
        description: str,
    ):
        super().__init__()
        self._setting = setting
        self._description = description

    @property
    def setting(self) -> Setting:
        return self._setting

    @property
    def value(self):
        return self._setting.get_value()

    def reset(self) -> None:
        pass

    def render(self, layout: QtWidgets.QFormLayout) -> None:
        pass


class BooleanSettingEditor(SettingEditor):
    setting_type = bool

    def __init__(
        self,
        setting: Setting,
        description: str,
    ):
        super().__init__(setting, description)

        self._label = HoverLabel(self._setting.name, self._description)
        self._box = QtWidgets.QCheckBox()

        self._box.stateChanged.connect(lambda v: self.selected.emit(self, v == 2))
        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def reset(self) -> None:
        self._box.setChecked(self.value)

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._box)


class StringSettingEditor(SettingEditor):
    setting_type = str

    def __init__(
        self,
        setting: Setting,
        description: str,
        *,
        hide_text: bool = False,
    ):
        super().__init__(setting, description)

        self._label = HoverLabel(self._setting.name, self._description)
        self._field = QtWidgets.QLineEdit()

        if hide_text:
            self._field.setEchoMode(QtWidgets.QLineEdit.Password)

        self._field.editingFinished.connect(lambda: self.selected.emit(self, self._field.text()))

        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def reset(self) -> None:
        self._field.setText(self.value)

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._field)


class IntegerSettingEditor(SettingEditor):
    setting_type = int

    def __init__(
        self,
        setting: Setting,
        description: str,
        *,
        min_value: t.Optional[int] = None,
        max_value: t.Optional[int] = None,
    ):
        super().__init__(setting, description)

        self._label = HoverLabel(self._setting.name, self._description)
        self._field = QtWidgets.QSpinBox()

        if min_value is not None:
            self._field.setMinimum(min_value)
        if max_value is not None:
            self._field.setMaximum(max_value)

        self._field.editingFinished.connect(lambda: self.selected.emit(self, self._field.text()))
        self._field.valueChanged.connect(lambda v: self.selected.emit(self, v))

        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def reset(self) -> None:
        self._field.setValue(self.value)

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._field)


class OptionsSettingEditor(SettingEditor):
    setting_type = str

    def __init__(
        self,
        setting: Setting,
        description: str,
        options: t.Sequence[str],
    ):
        super().__init__(setting, description)

        self._label = HoverLabel(self._setting.name, self._description)
        self._combo = QtWidgets.QComboBox()

        self._combo.addItems(options)

        self._combo.currentTextChanged.connect(lambda v: self.selected.emit(self, v))
        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def reset(self) -> None:
        self._combo.setCurrentText(self.value)

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._combo)


class AlchemySettingEditor(SettingEditor):
    setting_type = int

    def __init__(
        self,
        setting: Setting,
        description: str,
        model_type: object,
        field: QueryableAttribute,
    ):
        super().__init__(setting, description)

        self._model_type = model_type
        self._field = field

        self._pk_column = self._model_type.__mapper__.primary_key[0]

        self._label = HoverLabel(self._setting.name, self._description)
        self._combo = QtWidgets.QComboBox()

        self._combo.currentTextChanged.connect(
            lambda v: self.selected.emit(self, EDB.Session.query(self._pk_column).filter(self._field == v).scalar() or 0)
        )
        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

    def reset(self) -> None:
        self._combo.clear()
        self._combo.addItems(
            row
            for row, in
            EDB.Session.query(self._field)
        )
        model = EDB.Session.query(self._model_type).get(self.value)
        if model is None:
            self._combo.addItem('Select macro')
            model = 'Select macro'
        else:
            model = getattr(model, self._field.name)
        self._combo.setCurrentText(model)

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._combo)
