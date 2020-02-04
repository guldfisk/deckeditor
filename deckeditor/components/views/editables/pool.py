from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoStack

from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.context.context import Context
from deckeditor.models.deck import PoolModel


class PoolView(Editable):

    def __init__(
        self,
        pool_model: PoolModel,
        *,
        maindeck_cube_view: t.Optional[CubeView] = None,
        sideboard_cube_view: t.Optional[CubeView] = None,
        pool_cube_view: t.Optional[CubeEditMode] = None,
        undo_stack: t.Optional[QUndoStack] = None,
    ) -> None:
        super().__init__()

        self._undo_stack = undo_stack if undo_stack is not None else QUndoStack(Context.undo_group)
        QUndoStack(Context.undo_group)

        self._pool_model = pool_model

        layout = QtWidgets.QVBoxLayout()

        self._vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
        self._horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        self._maindeck_cube_view = (
            maindeck_cube_view
            if maindeck_cube_view is not None else
            CubeView(
                self._pool_model.maindeck,
                self._undo_stack,
            )
        )
        self._sideboard_cube_view = (
            sideboard_cube_view
            if sideboard_cube_view is not None else
            CubeView(
                self._pool_model.sideboard,
                self._undo_stack,
            )
        )
        self._pool_cube_view = (
            pool_cube_view
            if pool_cube_view is not None else
            CubeView(
                self._pool_model.pool,
                self._undo_stack,
            )
        )

        self._horizontal_splitter.addWidget(self._maindeck_cube_view)
        self._horizontal_splitter.addWidget(self._sideboard_cube_view)

        self._vertical_splitter.addWidget(self._pool_cube_view)
        self._vertical_splitter.addWidget(self._horizontal_splitter)

        layout.addWidget(self._vertical_splitter)

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

    def is_empty(self) -> bool:
        return not (
            self._pool_model.maindeck.items()
            or self._pool_model.sideboard.items()
            or self._pool_model.pool.items()
        )

    @property
    def pool_model(self) -> PoolModel:
        return self._pool_model

    def persist(self) -> t.Any:
        return {
            'maindeck_view': self._maindeck_cube_view.persist(),
            'sideboard_view': self._sideboard_cube_view.persist(),
            'pool_view': self._pool_cube_view.persist(),
            'horizontal_splitter': self._horizontal_splitter.saveState(),
            'vertical_splitter': self._vertical_splitter.saveState(),
            'pool_model': self._pool_model.persist(),
            'tab_type': 'pool',
        }

    @classmethod
    def load(cls, state: t.Any) -> PoolView:
        pool_model = PoolModel.load(state['pool_model'])
        undo_stack = QUndoStack(Context.undo_group)
        pool_view = cls(
            pool_model,
            maindeck_cube_view = CubeView.load(
                state['maindeck_view'],
                pool_model.maindeck,
                undo_stack = undo_stack,
            ),
            sideboard_cube_view = CubeView.load(
                state['sideboard_view'],
                pool_model.sideboard,
                undo_stack = undo_stack,
            ),
            pool_cube_view = CubeView.load(
                state['pool_view'],
                pool_model.pool,
                undo_stack = undo_stack,
            ),
            undo_stack = undo_stack,
        )
        pool_view._horizontal_splitter.restoreState(state['horizontal_splitter'])
        pool_view._vertical_splitter.restoreState(state['vertical_splitter'])
        return pool_view

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack
