import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QWidget, QUndoStack, QVBoxLayout

from deckeditor.components.views.cubeedit.cubelistview import CubeListView
from deckeditor.components.views.cubeedit.graphical.cubemultiimageview import CubeMultiImageView
from deckeditor.components.views.cubeedit.graphical.cubescene import CubeScene
from deckeditor.components.views.editables.editable import Editable
from deckeditor.context.context import Context
from deckeditor.models.deck import PoolModel


class PoolView(Editable):

    def __init__(
        self,
        pool_model: PoolModel,
        parent: t.Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._undo_stack = QUndoStack(Context.undo_group)
        Context.undo_group.setActiveStack(self._undo_stack)

        self._pool_model = pool_model

        layout = QtWidgets.QVBoxLayout()

        vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
        horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        horizontal_splitter.addWidget(
            CubeMultiImageView(
                CubeScene(
                    self._pool_model.maindeck,
                ),
                self._undo_stack,
            )
        )
        horizontal_splitter.addWidget(
            CubeMultiImageView(
                CubeScene(
                    self._pool_model.sideboard,
                ),
                self._undo_stack,
            )
        )

        vertical_splitter.addWidget(
            CubeMultiImageView(
                CubeScene(
                    self._pool_model.pool,
                ),
                self._undo_stack,
            )
        )
        vertical_splitter.addWidget(
            horizontal_splitter
        )

        layout.addWidget(vertical_splitter)

        self.setLayout(layout)

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack
