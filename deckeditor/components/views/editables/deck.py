from __future__ import annotations

import typing as t
import uuid

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QVBoxLayout, QUndoStack

from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.context.context import Context
from deckeditor.models.deck import DeckModel


class DeckView(Editable):

    def __init__(
        self,
        deck_model: DeckModel,
        file_path: t.Optional[str] = None,
        *,
        maindeck_cube_view: t.Optional[CubeView] = None,
        sideboard_cube_view: t.Optional[CubeView] = None,
        undo_stack: t.Optional[QUndoStack] = None
    ) -> None:
        super().__init__()
        self._file_path = file_path
        self._uuid = str(uuid.uuid4())

        self._undo_stack = undo_stack if undo_stack is not None else QUndoStack(Context.undo_group)

        self._deck_model = deck_model

        layout = QVBoxLayout()

        self._horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        self._maindeck_cube_view = (
            maindeck_cube_view
            if maindeck_cube_view is not None else
            CubeView(
                self._deck_model.maindeck,
                self._undo_stack,
            )
        )

        self._sideboard_cube_view = (
            sideboard_cube_view
            if sideboard_cube_view is not None else
            CubeView(
                self._deck_model.sideboard,
                self._undo_stack,
            )
        )

        self._horizontal_splitter.addWidget(self._maindeck_cube_view)
        self._horizontal_splitter.addWidget(self._sideboard_cube_view)

        layout.addWidget(self._horizontal_splitter)

        self.setLayout(layout)

        self._maindeck_cube_view.cube_image_view.card_double_clicked.connect(
            lambda card: self._undo_stack.push(
                self._maindeck_cube_view.cube_scene.get_inter_move(
                    [card],
                    self._sideboard_cube_view.cube_scene,
                    QPoint(),
                )
            )
        )
        self._sideboard_cube_view.cube_image_view.card_double_clicked.connect(
            lambda card: self._undo_stack.push(
                self._sideboard_cube_view.cube_scene.get_inter_move(
                    [card],
                    self._maindeck_cube_view.cube_scene,
                    QPoint(),
                )
            )
        )

    def is_empty(self) -> bool:
        return not (self._deck_model.maindeck.items() or self._deck_model.sideboard.items())

    def persist(self) -> t.Any:
        return {
            'maindeck_view': self._maindeck_cube_view.persist(),
            'sideboard_view': self._sideboard_cube_view.persist(),
            'splitter': self._horizontal_splitter.saveState(),
            'deck_model': self._deck_model.persist(),
            'tab_type': 'deck',
        }

    @classmethod
    def load(cls, state: t.Any) -> DeckView:
        deck_model = DeckModel.load(state['deck_model'])
        undo_stack = QUndoStack(Context.undo_group)
        deck_view = DeckView(
            deck_model,
            maindeck_cube_view = CubeView.load(
                state['maindeck_view'],
                deck_model.maindeck,
                undo_stack = undo_stack,
            ),
            sideboard_cube_view = CubeView.load(
                state['sideboard_view'],
                deck_model.sideboard,
                undo_stack = undo_stack,
            ),
            undo_stack = undo_stack,
        )
        deck_view._horizontal_splitter.restoreState(state['splitter'])
        return deck_view

    @property
    def file_path(self) -> t.Optional[str]:
        return self._file_path

    def get_key(self) -> str:
        if self._file_path is not None:
            return self._file_path
        return self._uuid

    @property
    def deck_model(self) -> DeckModel:
        return self._deck_model

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack
