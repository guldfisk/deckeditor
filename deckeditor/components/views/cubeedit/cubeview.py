from __future__ import annotations

import os
import typing as t
from collections import OrderedDict
from enum import Enum

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QUndoStack

from deckeditor import paths
from deckeditor.components.views.cubeedit.cubelistview import CubeListView
from deckeditor.models.cubes.alignment.aligner import Aligner
from deckeditor.models.cubes.alignment.grid import GridAligner
from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.components.views.cubeedit.graphical.cubeimageview import CubeImageView
from deckeditor.models.cubes.cubescene import CubeScene

from deckeditor.context.context import Context


ALIGNER_TYPE_MAP = OrderedDict(
    (
        ('Static Stacking Grid', StaticStackingGrid),
        ('Grid', GridAligner),
        # 'Dynamic Stacking Grid': DynamicStackingGrid,
    )
)


class CubeViewLayout(Enum):
    IMAGE = 'image-line.svg'
    MIXED = 'checkbox-multiple-line.svg'
    TABLE = 'file-text-line.svg'


class LayoutSelector(QtWidgets.QPushButton):

    def __init__(self, cube_view: CubeView):
        super().__init__()
        self._cube_view = cube_view
        self._on_layout_changed(self._cube_view.view_layout)
        self._cube_view.layout_changed.connect(self._on_layout_changed)
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self) -> None:
        layouts = list(CubeViewLayout)
        current_index = layouts.index(self._cube_view.view_layout)
        self._cube_view.layout_changed.emit(
            layouts[(current_index + 1) % len(layouts)]
        )

    def _on_layout_changed(self, layout: CubeViewLayout) -> None:
        self.setIcon(
            QIcon(
                os.path.join(paths.ICONS_PATH, layout.value)
            )
        )


class SelectedInfo(QtWidgets.QLabel):

    def set_amount_selected(self, selected: int = 0):
        self.setText(f'{selected} selected items')


class AlignSelector(QtWidgets.QComboBox):

    def __init__(self, cube_scene: CubeScene, undo_stack: QUndoStack):
        super().__init__()

        self._cube_scene = cube_scene
        self._undo_stack = undo_stack

        self._cube_scene.aligner_changed.connect(self._on_aligner_change)

        for name, aligner_type in ALIGNER_TYPE_MAP.items():
            self.addItem(name, aligner_type)

        self.setCurrentIndex(
            self.findData(StaticStackingGrid)
        )

        self._cube_scene.aligner_changed.connect(self._on_aligner_change)
        self.activated.connect(self._on_index_change)

    def _on_index_change(self, idx: int) -> None:
        aligner_type = self.itemData(idx)

        self._undo_stack.push(
            self._cube_scene.get_set_aligner(
                aligner_type
            )
        )

    def _on_aligner_change(self, aligner: Aligner) -> None:
        if aligner != self.currentData():
            self.setCurrentIndex(
                self.findData(
                    type(aligner)
                )
            )


class SelectionIndicator(QtWidgets.QLabel):

    def __init__(self, scene: CubeScene):
        super().__init__()
        self._scene = scene
        self._reset_text()

        self._scene.selectionChanged.connect(self._reset_text)

    def _reset_text(self) -> None:
        self.setText(
            '{}/{}'.format(
                len(self._scene.selectedItems()),
                len(self._scene.items()),
            )
        )


class CubeView(QtWidgets.QWidget):
    layout_changed = QtCore.pyqtSignal(CubeViewLayout)

    def __init__(self, scene: CubeScene, undo_stack: QUndoStack, parent = None):
        super().__init__(parent = parent)

        self._cube_scene = scene

        self._undo_stack = undo_stack

        self._current_aligner_type = StaticStackingGrid
        self._view_layout = CubeViewLayout.IMAGE

        self._cube_image_view = CubeImageView(
            undo_stack,
            self._cube_scene
        )

        self._cube_list_view = CubeListView(
            self._cube_scene,
            undo_stack,
        )
        self._cube_list_view.hide()

        self._aligner_selector = AlignSelector(self._cube_scene, self._undo_stack)

        self._selection_indicator = SelectionIndicator(self._cube_scene)

        self._layout_selector = LayoutSelector(self)
        self._layout_selector.setFixedSize(QSize(20, 20))


        box = QtWidgets.QVBoxLayout(self)

        self._tool_bar = QtWidgets.QHBoxLayout(self)

        self._tool_bar.addWidget(self._aligner_selector)
        self._tool_bar.addWidget(self._selection_indicator)
        self._tool_bar.addWidget(self._layout_selector)

        box.addLayout(self._tool_bar)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        splitter.addWidget(self._cube_image_view)
        splitter.addWidget(self._cube_list_view)

        box.addWidget(splitter)

        self.setLayout(box)

        self.layout_changed.connect(self._on_layout_change)

    @property
    def view_layout(self) -> CubeViewLayout:
        return self._view_layout

    def _on_layout_change(self, layout: CubeViewLayout) -> None:
        self._view_layout = layout
        if layout == CubeViewLayout.TABLE:
            self._cube_image_view.hide()
            self._cube_list_view.show()

        elif layout == CubeViewLayout.IMAGE:
            self._cube_image_view.show()
            self._cube_list_view.hide()

        elif layout == CubeViewLayout.MIXED:
            self._cube_image_view.show()
            self._cube_list_view.show()