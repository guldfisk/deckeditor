from __future__ import annotations

import random
import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget

from magiccube.collections.cubeable import Cubeable
from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.grid import GridAligner
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.utils.actions import WithActions


class SampleHandView(QtWidgets.QWidget, WithActions):

    def __init__(self, deck_scene: CubeScene, *, parent: t.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._deck_scene = deck_scene

        self._undo_stack = Context.get_undo_stack()

        self._hand_scene = CubeScene(
            aligner_type = GridAligner,
            mode = CubeEditMode.CLOSED,
            name = 'Sample Hand',
        )

        self._hand_view = CubeView(self._hand_scene, self._undo_stack)

        self._draw_hand_button = QtWidgets.QPushButton('Draw Hand')
        self._draw_hand_button.clicked.connect(self.refresh)

        self._create_shortcut(self.refresh, 'h')

        self._draw_card_button = QtWidgets.QPushButton('Draw Card')
        self._draw_card_button.clicked.connect(lambda: self.add_cubeables(1))

        self._create_shortcut(self.add_cubeables, 'd')

        layout = QtWidgets.QVBoxLayout(self)

        control_bar = QtWidgets.QHBoxLayout()
        control_bar.addWidget(self._draw_hand_button)
        control_bar.addWidget(self._draw_card_button)

        layout.addWidget(self._hand_view)
        layout.addLayout(control_bar)

    def _get_cubeables(self, amount: int = 1) -> t.List[Cubeable]:
        remaining_cubeables = list(self._deck_scene.cube - self._hand_scene.cube)
        if len(remaining_cubeables) <= amount:
            return remaining_cubeables

        return random.sample(remaining_cubeables, amount)

    def add_cubeables(self, amount: int = 1) -> None:
        add = self._get_cubeables(amount)
        if add:
            self._hand_scene.get_cube_modification(
                CubeDeltaOperation(
                    add
                ),
                closed_operation = True,
            ).redo()
        self._undo_stack.clear()

    def refresh(self) -> None:
        remove = self._hand_scene.items()
        if remove:
            self._hand_scene.get_cube_modification(
                remove = remove,
                closed_operation = True,
            ).redo()
        self.add_cubeables(7)


class SampleHandDialog(QtWidgets.QDialog):

    def __init__(self, deck_scene: CubeScene, *, parent: t.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._sample_view = SampleHandView(deck_scene)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._sample_view)

        self._sample_view.refresh()
