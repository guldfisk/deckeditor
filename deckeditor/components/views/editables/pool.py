from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoStack, QGraphicsScene

from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import TabType
from deckeditor.components.views.editables.multicubesview import MultiCubesView
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.deck import PoolModel


class PoolView(MultiCubesView):

    def __init__(
        self,
        pool_model: PoolModel,
        undo_stack: QUndoStack,
        *,
        maindeck_cube_view: t.Optional[CubeView] = None,
        sideboard_cube_view: t.Optional[CubeView] = None,
        pool_cube_view: t.Optional[CubeView] = None,
    ) -> None:
        super().__init__(undo_stack)

        self._pool_model = pool_model

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 1)

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

        self._all_scenes = {
            self._maindeck_cube_view.cube_scene,
            self._sideboard_cube_view.cube_scene,
            self._pool_cube_view.cube_scene,
        }

        for scene in self._all_scenes:
            scene.selection_cleared.connect(self._on_cube_scene_selection_cleared)

        self._horizontal_splitter.addWidget(self._maindeck_cube_view)
        self._horizontal_splitter.addWidget(self._sideboard_cube_view)

        self._vertical_splitter.addWidget(self._pool_cube_view)
        self._vertical_splitter.addWidget(self._horizontal_splitter)

        layout.addWidget(self._vertical_splitter)

        self._connect_move_cubeable(self._maindeck_cube_view, self._pool_cube_view, self._sideboard_cube_view)
        self._connect_move_cubeable(self._sideboard_cube_view, self._pool_cube_view, self._maindeck_cube_view)
        self._connect_move_cubeable(self._pool_cube_view, self._maindeck_cube_view, self._sideboard_cube_view)

    @property
    def cube_views(self) -> t.Iterable[CubeView]:
        return (
            self._pool_cube_view,
            self._maindeck_cube_view,
            self._sideboard_cube_view,
        )

    def _on_cube_scene_selection_cleared(self, scene: QGraphicsScene) -> None:
        for _scene in self._all_scenes:
            if _scene != scene:
                _scene.clear_selection(propagate = False)

    def _connect_move_cubeable(
        self,
        cube_view: CubeView,
        primary_target: CubeView,
        secondary_target: CubeView,
    ) -> None:
        def _card_double_clicked(card: PhysicalCard, modifiers: int) -> None:
            self._undo_stack.push(
                cube_view.cube_scene.get_inter_move(
                    [card],
                    (
                        secondary_target.cube_scene
                        if modifiers & QtCore.Qt.ShiftModifier else
                        primary_target.cube_scene
                    ),
                    QPoint(),
                )
            )

        cube_view.cube_image_view.card_double_clicked.connect(_card_double_clicked)

    def is_empty(self) -> bool:
        return not (
            self._pool_model.maindeck.items()
            or self._pool_model.sideboard.items()
            or self._pool_model.pool.items()
        )

    @property
    def pool_model(self) -> PoolModel:
        return self._pool_model

    @property
    def tab_type(self) -> TabType:
        return TabType.POOL

    def persist(self) -> t.Any:
        return {
            'maindeck_view': self._maindeck_cube_view.persist(),
            'sideboard_view': self._sideboard_cube_view.persist(),
            'pool_view': self._pool_cube_view.persist(),
            'horizontal_splitter': self._horizontal_splitter.saveState(),
            'vertical_splitter': self._vertical_splitter.saveState(),
            'pool_model': self._pool_model.persist(),
            'tab_type': self.tab_type,
        }

    @classmethod
    def load(cls, state: t.Any, undo_stack: QUndoStack) -> PoolView:
        pool_model = PoolModel.load(state['pool_model'])
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
