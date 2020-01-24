import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QWidget, QUndoStack

from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.components.views.cubeedit.cubeview import CubeView
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
        # Context.undo_group.setActiveStack(self._undo_stack)

        self._pool_model = pool_model

        layout = QtWidgets.QVBoxLayout()

        vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
        horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        self._maindeck_cube_view = CubeView(
            self._pool_model.maindeck,
            self._undo_stack,
            CubeEditMode.CLOSED,
        )
        self._sideboard_cube_view = CubeView(
            self._pool_model.sideboard,
            self._undo_stack,
            CubeEditMode.CLOSED,
        )
        self._pool_cube_view = CubeView(
            self._pool_model.pool,
            self._undo_stack,
            CubeEditMode.CLOSED,
        )

        horizontal_splitter.addWidget(self._maindeck_cube_view)
        horizontal_splitter.addWidget(self._sideboard_cube_view)

        vertical_splitter.addWidget(self._pool_cube_view)
        vertical_splitter.addWidget(
            horizontal_splitter
        )

        layout.addWidget(vertical_splitter)

        self.setLayout(layout)

        # TODO dry this shit, also in deckview
        self._maindeck_cube_view.cube_image_view.card_double_clicked.connect(
            lambda card: self._undo_stack.push(
                self._maindeck_cube_view.cube_scene.get_inter_move(
                    [card],
                    self._pool_cube_view.cube_scene,
                    QPoint(),
                )
            )
        )
        self._sideboard_cube_view.cube_image_view.card_double_clicked.connect(
            lambda card: self._undo_stack.push(
                self._sideboard_cube_view.cube_scene.get_inter_move(
                    [card],
                    self._pool_cube_view.cube_scene,
                    QPoint(),
                )
            )
        )
        self._pool_cube_view.cube_image_view.card_double_clicked.connect(
            lambda card: self._undo_stack.push(
                self._pool_cube_view.cube_scene.get_inter_move(
                    [card],
                    self._maindeck_cube_view.cube_scene,
                    QPoint(),
                )
            )
        )

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack
