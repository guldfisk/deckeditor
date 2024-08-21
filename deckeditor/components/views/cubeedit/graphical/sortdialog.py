from __future__ import annotations

import typing as t

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtWidgets import QCompleter, QDialog, QDialogButtonBox, QInputDialog
from sqlalchemy import func
from sqlalchemy.orm import Query, make_transient

from deckeditor.sorting.sorting import (
    DimensionContinuity,
    SortDimension,
    SortDirection,
    SortProperty,
)
from deckeditor.store import EDB
from deckeditor.store.models import SortMacro, SortSpecification
from deckeditor.utils.actions import WithActions
from deckeditor.utils.components.enumselector import EnumSelector
from deckeditor.utils.delegates import CheckBoxDelegate, ComboBoxDelegate
from deckeditor.utils.dialogs import SingleInstanceDialog
from deckeditor.utils.tables.alchemymodels import (
    EnumColumn,
    IndexedAlchemyModel,
    MappingColumn,
    PrimitiveColumn,
)
from deckeditor.utils.tables.dnd import ListDNDTable
from deckeditor.utils.tables.listdelete import LineDeleteMixin


class SortSpecificationDimensionModel(IndexedAlchemyModel[SortSpecification]):
    SORT_PROPERTY = MappingColumn(SortSpecification.sort_property, SortProperty.names_to_sort_property.items())
    DIRECTION = EnumColumn(SortSpecification.direction, SortDirection)
    RESPECT_CUSTOM = PrimitiveColumn(SortSpecification.respect_custom)

    def __init__(
        self,
        macro: SortMacro,
        dimension: SortDimension,
        *,
        page_size: int = 64,
        auto_commit: bool = False,
    ):
        super().__init__(
            model_type=SortSpecification,
            order_by=SortSpecification.index,
            page_size=page_size,
            auto_commit=auto_commit,
        )
        self._macro = macro
        self._dimension = dimension

    def filter_query(self, query: Query) -> Query:
        return query.filter(
            self._model_type.dimension == self._dimension,
            self._model_type.macro_id == self._macro.id,
        )

    def insert(self, item: SortSpecification, index: int) -> None:
        item.dimension = self._dimension
        super().insert(item, index)


class SortsTable(ListDNDTable, LineDeleteMixin):
    model: t.Callable[[], SortSpecificationDimensionModel]

    def __init__(self):
        super().__init__()

        self._delegate_classes = (
            (0, SortSpecificationDimensionModel.SORT_PROPERTY.preferred_delegate(self)),
            (1, SortSpecificationDimensionModel.DIRECTION.preferred_delegate(self)),
            (2, CheckBoxDelegate(self)),
        )

        for column, delegate in self._delegate_classes:
            self.setItemDelegateForColumn(column, delegate)

        self._enable_row_header_delete()

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if isinstance(event.source(), self.__class__):
            event.accept()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        event.acceptProposedAction()
        target_row = self.rowAt(event.pos().y())
        if target_row < 0:
            target_row = self.model().rowCount() - 1

        source: SortsTable = event.source()

        if source == self:
            if self.dragging_index != target_row:
                self.model().moveRow(
                    QModelIndex(),
                    self.dragging_index,
                    QModelIndex(),
                    target_row if target_row < self.dragging_index else target_row + 1,
                )
        else:
            specification = source.model().pop(source.dragging_index)
            make_transient(specification)
            self.model().insert(
                specification,
                min(target_row + 1, self.model().rowCount()),
            )

        source.dragging_index = None

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            (sum(self.columnWidth(i) for i in range(self.model().columnCount())) + 10) if self.model() else 10,
            200,
        )

    def setModel(self, model: QtCore.QAbstractItemModel) -> None:
        super().setModel(model)
        self.resizeColumnsToContents()


class MacrosTable(ListDNDTable, LineDeleteMixin):
    def __init__(self):
        super().__init__()

        delegate = ComboBoxDelegate([c.value for c in DimensionContinuity], self)

        for column in range(1, 4):
            self.setItemDelegateForColumn(column, delegate)

        self._enable_row_header_delete()

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            sum(self.columnWidth(i) for i in range(self.model().columnCount())) + 10,
            200,
        )

    def setModel(self, model: QtCore.QAbstractItemModel) -> None:
        super().setModel(model)
        self.resizeColumnsToContents()


class SortPropertySelector(QtWidgets.QLineEdit):
    sort_property_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        completer = QCompleter(sorted(SortProperty.names_to_sort_property.keys()))
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setModelSorting(QCompleter.CaseSensitivelySortedModel)
        completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(completer)

    def focusInEvent(self, focus_event: QtGui.QFocusEvent):
        super().focusInEvent(focus_event)
        self.selectAll()

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            super().keyPressEvent(key_event)

            try:
                sort_property = SortProperty.names_to_sort_property[self.text()]
            except KeyError:
                fragments = self.text().split(" ")
                if not fragments:
                    return
                for key in sorted(SortProperty.names_to_sort_property.keys()):
                    if all(fragment.lower() in key.lower() for fragment in fragments):
                        self.setText(key)
                        return
                return

            else:
                self.sort_property_selected.emit(sort_property)

        else:
            super().keyPressEvent(key_event)


class SortSpecificationSelector(QtWidgets.QWidget, WithActions):
    sort_specification_selected = pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Sort")

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._sort_selector = SortPropertySelector()
        self._sort_selector.sort_property_selected.connect(self._on_sort_property_selected)

        self._dimension_selector: EnumSelector[SortDimension] = EnumSelector(SortDimension)
        self._direction_selector: EnumSelector[SortDirection] = EnumSelector(SortDirection)

        self._respect_custom_box = QtWidgets.QCheckBox("Respect custom sort values")
        self._respect_custom_box.setChecked(True)

        self._macroes_table = QtWidgets.QTableView()

        layout.addWidget(self._sort_selector, 0, 0, 1, 3)
        layout.addWidget(self._dimension_selector, 1, 0, 1, 1)
        layout.addWidget(self._direction_selector, 1, 1, 1, 1)
        layout.addWidget(self._respect_custom_box, 1, 2, 1, 1)

        def set_dimension(dimension: SortDimension) -> t.Callable[[], None]:
            return lambda: self._dimension_selector.set_value(dimension)

        self._create_action("Auto Dimension", set_dimension(SortDimension.AUTO), "Alt+Q")
        self._create_action("Horizontal Dimension", set_dimension(SortDimension.HORIZONTAL), "Alt+W")
        self._create_action("Vertical Dimension", set_dimension(SortDimension.VERTICAL), "Alt+E")
        self._create_action("Sub Divisions Dimension", set_dimension(SortDimension.SUB_DIVISIONS), "Alt+R")

        def set_direction(direction: SortDirection) -> t.Callable[[], None]:
            return lambda: self._direction_selector.set_value(direction)

        self._create_action("Auto Direction", set_direction(SortDirection.AUTO), "Alt+A")
        self._create_action("Ascending Direction", set_direction(SortDirection.ASCENDING), "Alt+S")
        self._create_action("Descending Direction", set_direction(SortDirection.DESCENDING), "Alt+D")

        self._create_action(
            "Toggle Respect Custom",
            lambda: self._respect_custom_box.setChecked(not self._respect_custom_box.isChecked()),
            "Alt+F",
        )

        self.setLayout(layout)

    def _on_sort_property_selected(self, sort_property: t.Type[SortProperty]) -> None:
        self.sort_specification_selected.emit(
            SortSpecification(
                sort_property=sort_property,
                dimension=self._dimension_selector.get_value(),
                direction=self._direction_selector.get_value(),
                respect_custom=self._respect_custom_box.isChecked(),
            )
        )


class SortSpecificationSelectorDialog(SingleInstanceDialog):
    sort_specification_selected = pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("New sort specification")

        layout = QtWidgets.QVBoxLayout(self)

        self._sort_specification_selector = SortSpecificationSelector()
        self._sort_specification_selector.sort_specification_selected.connect(self._on_sort_specification_selected)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self._buttons.rejected.connect(self._on_cancel)

        layout.addWidget(self._sort_specification_selector)
        layout.addWidget(self._buttons)

    def _on_sort_specification_selected(self, sort_specification: SortSpecification) -> None:
        self.accept()
        self.sort_specification_selected.emit(sort_specification)

    def _on_cancel(self) -> None:
        self.reject()


class EditMacroesDialog(QDialog, WithActions):
    selection_done = pyqtSignal(object, int, bool)
    sort_selected = pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Sort")

        layout = QtWidgets.QGridLayout(self)

        self._macro_name_label = QtWidgets.QLabel()

        self._horizontal_table = SortsTable()
        self._vertical_table = SortsTable()
        self._sub_table = SortsTable()

        self._macroes_model: IndexedAlchemyModel[SortMacro] = IndexedAlchemyModel(
            model_type=SortMacro,
            order_by=SortMacro.index,
            columns=[
                PrimitiveColumn(SortMacro.name),
                EnumColumn(SortMacro.horizontal_continuity, DimensionContinuity),
                EnumColumn(SortMacro.vertical_continuity, DimensionContinuity),
                EnumColumn(SortMacro.sub_continuity, DimensionContinuity),
            ],
            auto_commit=False,
        )
        self._macroes_table = MacrosTable()
        self._macroes_table.setModel(self._macroes_model)
        self._macroes_table.selectionModel().currentChanged.connect(self._on_macro_selected)

        self._new_macro_button = QtWidgets.QPushButton("New Macro")
        self._new_macro_button.clicked.connect(self._on_new_macro)
        self._new_macro_button.setShortcut("Ctrl+Shift+N")

        self._add_specification_button = QtWidgets.QPushButton("New Specification")
        self._add_specification_button.clicked.connect(self._on_add_sort_specification)
        self._add_specification_button.setShortcut("Ctrl+N")
        self._add_specification_button.setDisabled(True)

        layout.addWidget(self._macro_name_label, 0, 0, 1, 1)

        layout.addWidget(QtWidgets.QLabel("Horizontal"), 1, 0, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Vertical"), 1, 1, 1, 1)
        layout.addWidget(QtWidgets.QLabel("Sub Divisions"), 1, 2, 1, 1)

        layout.addWidget(self._horizontal_table, 2, 0, 1, 1)
        layout.addWidget(self._vertical_table, 2, 1, 1, 1)
        layout.addWidget(self._sub_table, 2, 2, 1, 1)

        layout.addWidget(self._macroes_table, 3, 0, 1, 2)

        macro_buttons = QtWidgets.QVBoxLayout()

        macro_buttons.addWidget(self._new_macro_button)
        macro_buttons.addWidget(self._add_specification_button)

        macro_buttons.addStretch()

        layout.addLayout(macro_buttons, 3, 2, 1, 1)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self._on_cancel)

        layout.addWidget(self._buttons, 4, 0, 1, 3)

        SortSpecificationSelectorDialog.get().sort_specification_selected.connect(self._on_sort_specification_selected)

        self._macro: t.Optional[SortMacro] = None

        self._new_focus_macro(self._macroes_model.get_item_at_index(0))

    def _on_add_sort_specification(self) -> None:
        SortSpecificationSelectorDialog.get().exec_()

    def _on_macro_selected(self, current: QModelIndex, previous: QModelIndex) -> None:
        macro = self._macroes_model.get_item_at_index(current.row())
        self._new_focus_macro(macro)

    def _new_focus_macro(self, macro: t.Optional[SortMacro]) -> None:
        self._macro = macro

        if macro is None:
            for table in (
                self._horizontal_table,
                self._vertical_table,
                self._sub_table,
            ):
                table.setModel(None)
            self._add_specification_button.setDisabled(True)
            self._macro_name_label.setText("")
            return

        for table, dimension in (
            (self._horizontal_table, SortDimension.HORIZONTAL),
            (self._vertical_table, SortDimension.VERTICAL),
            (self._sub_table, SortDimension.SUB_DIVISIONS),
        ):
            table.setModel(
                SortSpecificationDimensionModel(
                    macro=macro,
                    dimension=dimension,
                )
            )
        self._add_specification_button.setDisabled(False)
        self._macro_name_label.setText(macro.name)

    def _on_new_macro(self) -> None:
        next_index = EDB.Session.query(func.max(SortMacro.index)).scalar()
        next_index = 0 if next_index is None else next_index + 1
        macro_name, success = QInputDialog.getText(
            self,
            "Save macro",
            "Choose name",
            text="Macro {}".format(next_index),
        )
        if not success:
            return
        macro = SortMacro(name=macro_name, index=next_index)
        EDB.Session.add(macro)
        self._macroes_model.reset()
        self._macroes_table.selectionModel().setCurrentIndex(
            self._macroes_model.createIndex(next_index, 0, None),
            QtCore.QItemSelectionModel.ClearAndSelect,
        )

    def _on_ok(self) -> None:
        EDB.Session.commit()
        self.accept()

    def _on_cancel(self) -> None:
        EDB.Session.rollback()
        self.reject()

    def _on_sort_specification_selected(self, sort_specification: SortSpecification) -> None:
        dimension = sort_specification.dimension.dimension_for(sort_specification.sort_property)
        sort_specification.dimension = dimension

        if dimension == SortDimension.HORIZONTAL:
            table = self._horizontal_table
        elif dimension == SortDimension.SUB_DIVISIONS:
            table = self._sub_table
        else:
            table = self._vertical_table

        sort_specification.macro = self._macro
        table.model().append(sort_specification)
