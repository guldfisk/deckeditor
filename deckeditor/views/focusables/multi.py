import os
import typing
import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget

from mtgimg.interface import SizeSlug

from deckeditor import paths
from deckeditor.components.cardview.cubeableview import F
from deckeditor.models.focusables.grid import CubeablesGrid
from deckeditor.models.focusables.lists import CardboardList
from deckeditor.models.sequence import GenericItemSequence
from deckeditor.utils.actions import WithActions
from deckeditor.views.focusables.grid import FocusableGridView
from deckeditor.views.focusables.lists import FocusableListSelector


class FocusableMultiView(t.Generic[F], QtWidgets.QStackedWidget, WithActions):
    focusable_selected = pyqtSignal(object)
    current_focusable_changed = pyqtSignal(object)

    def __init__(
        self,
        parent: typing.Optional[QWidget] = None,
        *,
        image_mode: bool = False,
        image_size: SizeSlug = SizeSlug.SMALL,
    ) -> None:
        super().__init__(parent)
        self._grid_proxy = CubeablesGrid()

        self._list_selector: FocusableListSelector[F] = FocusableListSelector()
        self._list_selector.focusable_selected.connect(self.focusable_selected)
        self._list_selector.current_focusable_changed.connect(self.current_focusable_changed)

        self._grid = FocusableGridView(size_slug = image_size)
        self._grid.focusable_selected.connect(self.focusable_selected)
        self._grid.current_focusable_changed.connect(self.current_focusable_changed)

        self._image_mode = None
        self._button = QtWidgets.QPushButton(self)
        self._button.setFocusPolicy(QtCore.Qt.NoFocus)
        self._button.setFixedSize(QSize(20, 20))

        self._button.clicked.connect(lambda: self.set_mode(not self._image_mode))

        self.set_model(CardboardList())

        self._grid.setModel(self._grid_proxy)

        self.addWidget(self._list_selector)
        self.addWidget(self._grid)

        self._move_button()

        self.set_mode(image_mode)

        self._create_action('View Images', lambda: self.set_mode(True), 'Alt+I')
        self._create_action('View Table', lambda: self.set_mode(False), 'Alt+T')

    def set_mode(self, image_mode: bool) -> None:
        if image_mode == self._image_mode:
            return

        self._image_mode = image_mode
        self.setCurrentWidget(
            self._grid if image_mode else self._list_selector
        )
        self._button.raise_()
        self._button.setIcon(
            QIcon(
                os.path.join(
                    paths.ICONS_PATH,
                    'image-line.svg' if image_mode else 'file-text-line.svg',
                )
            )
        )

    def set_model(self, model: GenericItemSequence[F]) -> None:
        self._list_selector.setModel(model)
        self._grid_proxy.setSourceModel(model)

    def _move_button(self) -> None:
        self._button.move(
            self.width() - self._button.width() - 20,
            self.height() - self._button.height() - 20,
        )

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        self._move_button()

    def refocus(self) -> None:
        widget = self.currentWidget()
        widget.setCurrentIndex(widget.model().index(0, 0))
        widget.setFocus()

