from __future__ import annotations

import typing as t
import uuid

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QVBoxLayout, QUndoStack, QGraphicsScene

from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import TabType
from deckeditor.components.views.editables.multicubesview import MultiCubesView
from deckeditor.models.deck import DeckModel


class DeckView(MultiCubesView):

    def __init__(
        self,
        deck_model: DeckModel,
        undo_stack: QUndoStack,
        file_path: t.Optional[str] = None,
        *,
        maindeck_cube_view: t.Optional[CubeView] = None,
        sideboard_cube_view: t.Optional[CubeView] = None,
    ) -> None:
        super().__init__(undo_stack)
        self._file_path = file_path
        self._uuid = str(uuid.uuid4())

        self._deck_model = deck_model

        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 1)

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

        self._all_scenes = {
            self._maindeck_cube_view.cube_scene,
            self._sideboard_cube_view.cube_scene,
        }

        for scene in self._all_scenes:
            scene.selection_cleared.connect(self._on_cube_scene_selection_cleared)

        self._horizontal_splitter.addWidget(self._maindeck_cube_view)
        self._horizontal_splitter.addWidget(self._sideboard_cube_view)

        layout.addWidget(self._horizontal_splitter)

        self.setLayout(layout)

        self._maindeck_cube_view.cube_image_view.card_double_clicked.connect(
            lambda card, _: self._undo_stack.push(
                self._maindeck_cube_view.cube_scene.get_inter_move(
                    [card],
                    self._sideboard_cube_view.cube_scene,
                    QPoint(),
                )
            )
        )
        self._sideboard_cube_view.cube_image_view.card_double_clicked.connect(
            lambda card, _: self._undo_stack.push(
                self._sideboard_cube_view.cube_scene.get_inter_move(
                    [card],
                    self._maindeck_cube_view.cube_scene,
                    QPoint(),
                )
            )
        )

    @property
    def cube_views(self) -> t.Iterable[CubeView]:
        return (
            self._maindeck_cube_view,
            self._sideboard_cube_view,
        )

    def _on_cube_scene_selection_cleared(self, scene: QGraphicsScene) -> None:
        for _scene in self._all_scenes:
            if _scene != scene:
                _scene.clear_selection(propagate = False)

    def is_empty(self) -> bool:
        return not (self._deck_model.maindeck.items() or self._deck_model.sideboard.items())

    @property
    def tab_type(self) -> TabType:
        return TabType.DECK

    def persist(self) -> t.Any:
        return {
            'maindeck_view': self._maindeck_cube_view.persist(),
            'sideboard_view': self._sideboard_cube_view.persist(),
            'splitter': self._horizontal_splitter.saveState(),
            'deck_model': self._deck_model.persist(),
            'tab_type': self.tab_type,
        }

    @classmethod
    def load(cls, state: t.Any, undo_stack: QUndoStack) -> DeckView:
        deck_model = DeckModel.load(state['deck_model'])
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
    def deck_model(self) -> DeckModel:
        return self._deck_model
