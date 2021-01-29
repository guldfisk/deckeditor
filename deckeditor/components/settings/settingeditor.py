from __future__ import annotations

import typing as t
from abc import abstractmethod

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QObject

from sqlalchemy.orm.attributes import QueryableAttribute

from hardcandy import fields

from deckeditor.components.settings.settings import Setting
from deckeditor.models.cubes.alignment.aligner import Aligner
from deckeditor.models.cubes.alignment.aligners import ALIGNER_TYPE_MAP
from deckeditor.models.cubes.scenetypes import SceneType
from deckeditor.store import EDB
from deckeditor.store.models import SortMacro


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


class AlignerOption(QtWidgets.QWidget):
    value_changed = pyqtSignal(object)

    def __init__(self, field: fields.Field):
        super().__init__()
        self._field = field
        self._layout = QtWidgets.QVBoxLayout(self)

    @abstractmethod
    def set_value(self, value: t.Any) -> None:
        pass


class IntegerAlignerOption(AlignerOption):

    def __init__(self, field: fields.Integer):
        super().__init__(field)

        self._selector = QtWidgets.QSpinBox()
        if field.min is not None:
            self._selector.setMinimum(field.min)
        if field.max is not None:
            self._selector.setMaximum(field.max)

        self._selector.editingFinished.connect(lambda: self.value_changed.emit(int(self._selector.text())))

        self._layout.addWidget(self._selector)

    def set_value(self, value: int) -> None:
        self._selector.setValue(value)


class BooleanAlignerOption(AlignerOption):

    def __init__(self, field: fields.Integer):
        super().__init__(field)

        self._selector = QtWidgets.QCheckBox()

        self._selector.stateChanged.connect(lambda v: self.value_changed.emit(v == 2))

        self._layout.addWidget(self._selector)

    def set_value(self, value: bool) -> None:
        self._selector.setChecked(value)


_ALIGNER_OPTION_MAP: t.Mapping[t.Type[fields.Field], t.Type[AlignerOption]] = {
    fields.Integer: IntegerAlignerOption,
    fields.Bool: BooleanAlignerOption,
}


class AlignerOptionsPane(QtWidgets.QWidget):
    option_changed = pyqtSignal(str, str, object)

    def __init__(self, aligner: t.Type[Aligner]):
        super().__init__()
        self._aligner = aligner

        layout = QtWidgets.QFormLayout(self)

        self._options_map = {}

        for option in self._aligner.schema.fields.values():
            option_editor = _ALIGNER_OPTION_MAP[option.__class__](option)
            option_editor.value_changed.connect(self._get_option_callback(option))
            self._options_map[option.name] = option_editor
            layout.addRow(
                option.display_name,
                option_editor,
            )

    def _get_option_callback(self, option: fields.Field) -> t.Callable[[t.Any], None]:
        return lambda v: self.option_changed.emit(self._aligner.name, option.name, v)

    def set_values(self, values: t.Mapping[str, t.Any]) -> None:
        self.blockSignals(True)
        for k, v in values.items():
            self._options_map[k].set_value(v)
        self.blockSignals(False)


class SchemaSettingEditor(SettingEditor):
    setting_type = str

    def __init__(
        self,
        setting: Setting,
        description: str,
    ):
        super().__init__(setting, description)

        self._label = HoverLabel(self._setting.name, self._description)
        self._label.focus_description.connect(lambda d: self.show_description.emit(self, d))

        self._scene_type_selector = QtWidgets.QComboBox()
        self._scene_type_selector.addItems([scene_type.value for scene_type in SceneType])
        self._scene_type_selector.currentTextChanged.connect(self._on_scene_type_changed)

        self._aligner_type_selector = QtWidgets.QComboBox()
        self._aligner_type_selector.addItems(ALIGNER_TYPE_MAP.keys())
        self._aligner_type_selector.currentTextChanged.connect(self._on_aligner_type_changed)

        self._sort_selector = QtWidgets.QComboBox()
        self._sort_selector.currentTextChanged.connect(self._on_sort_changed)

        self._aligner_option_pane_stack = QtWidgets.QStackedWidget()
        self._aligner_options_map = {}

        self._current_value = self._load_value()

        for aligner_name, aligner_type in ALIGNER_TYPE_MAP.items():
            pane = AlignerOptionsPane(aligner_type)
            self._aligner_option_pane_stack.addWidget(pane)
            self._aligner_options_map[aligner_name] = pane
            pane.option_changed.connect(self._on_aligner_option_changed)

        self._container = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(self._container)
        layout.addRow('Scene Type', self._scene_type_selector)
        layout.addRow('Sort Macro', self._sort_selector)
        layout.addRow('Aligner', self._aligner_type_selector)
        layout.addRow('Aligner Options', self._aligner_option_pane_stack)

    def _load_value(self) -> t.Mapping[str, t.Any]:
        current_value = self.value
        for scene_type in SceneType:

            if scene_type.value not in current_value:
                current_value[scene_type.value] = {}

            if 'sort_macro' not in current_value[scene_type.value]:
                current_value[scene_type.value]['sort_macro'] = 0

            if 'aligner_type' not in current_value[scene_type.value]:
                current_value[scene_type.value]['aligner_type'] = 'Dynamic Stacking Grid'

            if 'aligner_options' not in current_value[scene_type.value]:
                current_value[scene_type.value]['aligner_options'] = ALIGNER_TYPE_MAP[
                    current_value[scene_type.value]['aligner_type']].schema.default

        return current_value

    def _on_scene_type_changed(self, scene_type: str) -> None:
        scene_values = self._current_value[scene_type]

        aligner_type = scene_values['aligner_type']

        self._aligner_type_selector.blockSignals(True)
        self._aligner_type_selector.setCurrentText(aligner_type)
        self._aligner_type_selector.blockSignals(False)

        self._sort_selector.blockSignals(True)
        self._sort_selector.setCurrentText(
            EDB.Session.query(SortMacro.name).filter(SortMacro.id == scene_values['sort_macro']).scalar() or 'Select Macro'
        )
        self._sort_selector.blockSignals(False)

        pane = self._aligner_options_map[aligner_type]
        self._aligner_option_pane_stack.setCurrentWidget(pane)
        pane.set_values(self._current_value[scene_type]['aligner_options'])

    def _on_sort_changed(self, macro_name: str) -> None:
        self._current_value[
            self._scene_type_selector.currentText()
        ]['sort_macro'] = EDB.Session.query(SortMacro.id).filter(SortMacro.name == macro_name).scalar() or 0
        self.selected.emit(self, self._current_value)

    def _on_aligner_type_changed(self, aligner_type: str) -> None:
        pane = self._aligner_options_map[aligner_type]

        self._aligner_option_pane_stack.setCurrentWidget(pane)

        default_options = ALIGNER_TYPE_MAP[aligner_type].schema.default

        current_scene_values = self._current_value[self._scene_type_selector.currentText()]

        current_scene_values['aligner_options'] = default_options
        current_scene_values['aligner_type'] = aligner_type

        pane.set_values(default_options)
        self.selected.emit(self, self._current_value)

    def _on_aligner_option_changed(self, aligner_type: str, option: str, value: t.Any, ) -> None:
        self._current_value[
            self._scene_type_selector.currentText()
        ]['aligner_options'][option] = value
        self.selected.emit(self, self._current_value)

    def reset(self) -> None:
        self._sort_selector.blockSignals(True)
        self._sort_selector.clear()
        self._sort_selector.addItems(
            row
            for row, in
            EDB.Session.query(SortMacro.name)
        )
        if not self._sort_selector.count():
            self._sort_selector.addItem('Select macro')
        self._sort_selector.blockSignals(False)

        self._current_value = self._load_value()
        self._scene_type_selector.blockSignals(True)
        self._scene_type_selector.setCurrentText(SceneType.MAINDECK.value)
        self._scene_type_selector.blockSignals(False)
        self._scene_type_selector.currentTextChanged.emit(self._scene_type_selector.currentText())

    def render(self, layout: QtWidgets.QFormLayout):
        layout.addRow(self._label, self._container)
