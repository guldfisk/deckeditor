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
from deckeditor.serialization.deckserializer import DeckSerializer
from deckeditor.values import SUPPORTED_EXTENSIONS


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

        horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

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

        horizontal_splitter.addWidget(self._maindeck_cube_view)
        horizontal_splitter.addWidget(self._sideboard_cube_view)
        layout.addWidget(
            horizontal_splitter
        )

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

    def persist(self) -> t.Any:
        return {
            'maindeck_view': self._maindeck_cube_view.persist(),
            'sideboard_view': self._sideboard_cube_view.persist(),
            'deck_model': self._deck_model.persist()
        }

    @classmethod
    def load(cls, state: t.Any) -> DeckView:
        deck_model = DeckModel.load(state['deck_model'])
        undo_stack = QUndoStack(Context.undo_group)
        return DeckView(
            deck_model,
            maindeck_cube_view = CubeView.load(
                state['maindeck_view'],
                deck_model.maindeck,
                CubeEditMode.OPEN,
                undo_stack = undo_stack,
            ),
            sideboard_cube_view = CubeView.load(
                state['sideboard_view'],
                deck_model.sideboard,
                CubeEditMode.OPEN,
                undo_stack = undo_stack,
            ),
            undo_stack = undo_stack,
        )

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

    def save(self) -> None:
        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dialog.setNameFilter(SUPPORTED_EXTENSIONS)
        dialog.setDefaultSuffix('json')

        if not dialog.exec_():
            return

        file_names = dialog.selectedFiles()

        if not file_names:
            return

        file_name = file_names[0]

        extension = file_name.split('.')[1]

        with open(file_name, 'w') as f:
            f.write(
                DeckSerializer.extension_to_serializer[extension].serialize(self._deck_model.as_deck())
            )
