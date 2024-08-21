from __future__ import annotations

import os
import typing as t
from enum import Enum

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QUndoStack

from deckeditor import paths
from deckeditor.components.settings import settings
from deckeditor.components.views.cubeedit.cubelistview import CubeListView
from deckeditor.components.views.cubeedit.graphical.cubeimageview import CubeImageView
from deckeditor.models.cubes.alignment.aligner import Aligner
from deckeditor.models.cubes.alignment.aligners import ALIGNER_TYPE_MAP
from deckeditor.models.cubes.cubelist import CubeList
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.utils.actions import WithActions
from deckeditor.utils.spoiler import Spoiler
from deckeditor.utils.transform import deserialize_transform, serialize_transform


class CubeViewLayout(Enum):
    IMAGE = "image-line.svg"
    MIXED = "checkbox-multiple-line.svg"
    TABLE = "file-text-line.svg"


class LayoutSelector(QtWidgets.QPushButton):
    def __init__(self, cube_view: CubeView):
        super().__init__()
        self._cube_view = cube_view
        self._on_layout_changed(self._cube_view.view_layout)
        self._cube_view.layout_changed.connect(self._on_layout_changed)
        self.clicked.connect(self._on_clicked)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def _on_clicked(self) -> None:
        layouts = list(CubeViewLayout)
        current_index = layouts.index(self._cube_view.view_layout)
        self._cube_view.layout_changed.emit(layouts[(current_index + 1) % len(layouts)])

    def _on_layout_changed(self, layout: CubeViewLayout) -> None:
        self.setIcon(QIcon(os.path.join(paths.ICONS_PATH, layout.value)))


class AlignSelector(QtWidgets.QComboBox):
    def __init__(self, cube_scene: CubeScene, undo_stack: QUndoStack):
        super().__init__()
        self._cube_scene = cube_scene
        self._undo_stack = undo_stack

        self._cube_scene.aligner_changed.connect(self._on_aligner_change)

        for name, aligner_type in ALIGNER_TYPE_MAP.items():
            self.addItem(name, aligner_type)

        self.setCurrentIndex(self.findData(type(self._cube_scene.aligner)))

        self._cube_scene.aligner_changed.connect(self._on_aligner_change)
        self.activated.connect(self._on_index_change)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def _on_index_change(self, idx: int) -> None:
        aligner_type = self.itemData(idx)

        self._undo_stack.push(self._cube_scene.get_set_aligner(aligner_type))

    def _on_aligner_change(self, aligner: Aligner) -> None:
        if aligner != self.currentData():
            self.setCurrentIndex(self.findData(type(aligner)))


class SelectionIndicator(QtWidgets.QLabel):
    def __init__(self, scene: CubeScene):
        super().__init__()
        self._scene = scene
        self._reset_text()

        self._scene.selectionChanged.connect(self._reset_text)
        self._scene.changed.connect(self._reset_text)

    def _reset_text(self, *args, **kwargs) -> None:
        self.setText(
            "{}/{}".format(
                len(self._scene.selectedItems()),
                len(self._scene.items()),
            )
        )


class CubeView(QtWidgets.QWidget, WithActions):
    layout_changed = QtCore.pyqtSignal(CubeViewLayout)
    cubeable_double_clicked = QtCore.pyqtSignal(object)

    def __init__(
        self,
        scene: CubeScene,
        undo_stack: QUndoStack,
        *,
        cube_view_layout: CubeViewLayout = CubeViewLayout.IMAGE,
        cube_image_view: t.Optional[CubeImageView] = None,
    ):
        super().__init__()

        self._cube_scene = scene
        self._undo_stack = undo_stack

        self._current_aligner_type = type(self._cube_scene.aligner)
        self._view_layout = cube_view_layout

        if cube_image_view is None:
            self._cube_image_view = CubeImageView(
                undo_stack,
                self._cube_scene,
            )
        else:
            self._cube_image_view = cube_image_view
            self._cube_image_view.undo_stack = self._undo_stack

        cube_list_model = CubeList(self._cube_scene, undo_stack=self._undo_stack)
        sort_model = QtCore.QSortFilterProxyModel()
        sort_model.setSourceModel(cube_list_model)
        self._cube_list_view = CubeListView()
        self._cube_list_view.setModel(sort_model)
        self._cube_list_view.hide()

        self._aligner_selector = AlignSelector(self._cube_scene, self._undo_stack)

        self._layout_selector = LayoutSelector(self)
        self._layout_selector.setFixedSize(QSize(20, 20))

        box = QtWidgets.QVBoxLayout(self)
        box.setContentsMargins(0, 2, 0, 0)

        self._tool_bar = QtWidgets.QHBoxLayout()
        self._tool_bar.setContentsMargins(0, 3, 0, 0)

        self._tool_bar.addWidget(self._aligner_selector)
        self._tool_bar.addWidget(self._layout_selector)

        self._spoiler = Spoiler(not settings.DEFAULT_CUBEVIEW_HEADER_HIDDEN.get_value())
        self._spoiler.set_content_layout(self._tool_bar)

        box.addWidget(self._spoiler)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        splitter.addWidget(self._cube_image_view)
        splitter.addWidget(self._cube_list_view)

        box.addWidget(splitter)

        self.layout_changed.connect(self._on_layout_change)

        self._cube_list_view.cubeable_double_clicked.connect(self.cubeable_double_clicked)
        self._cube_image_view.card_double_clicked.connect(lambda c, m: self.cubeable_double_clicked.emit(c.cubeable))

        self._create_shortcut(lambda: self._spoiler.set_expanded(not self._spoiler.expanded), "G")

        self._create_shortcut(lambda: self.layout_changed.emit(CubeViewLayout.IMAGE), "I")
        self._create_shortcut(lambda: self.layout_changed.emit(CubeViewLayout.TABLE), "T")
        self._create_shortcut(lambda: self.layout_changed.emit(CubeViewLayout.MIXED), "M")

    @property
    def cube_scene(self) -> CubeScene:
        return self._cube_scene

    @property
    def cube_image_view(self) -> CubeImageView:
        return self._cube_image_view

    def persist(self) -> t.Any:
        return {
            "layout": self._view_layout.name,
            "image_view_transform": serialize_transform(self._cube_image_view.get_persistable_transform()),
        }

    @classmethod
    def load(cls, state: t.Any, cube_scene: CubeScene, undo_stack: QUndoStack) -> CubeView:
        cube_view = CubeView(
            cube_scene,
            undo_stack,
            cube_view_layout=CubeViewLayout[state["layout"]],
        )
        cube_view.cube_image_view.setTransform(deserialize_transform(state["image_view_transform"]))
        return cube_view

    @property
    def view_layout(self) -> CubeViewLayout:
        return self._view_layout

    def _on_layout_change(self, layout: CubeViewLayout) -> None:
        self._view_layout = layout
        if layout == CubeViewLayout.TABLE:
            self._cube_image_view.hide()
            self._cube_list_view.show()
            self._cube_list_view.setFocus()

        elif layout == CubeViewLayout.IMAGE:
            self._cube_image_view.show()
            self._cube_list_view.hide()
            self._cube_image_view.setFocus()

        elif layout == CubeViewLayout.MIXED:
            self._cube_image_view.show()
            self._cube_list_view.show()
