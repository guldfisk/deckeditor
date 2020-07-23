from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from deckeditor.components.lobbies.controller import LOBBIES_CONTROLLER
from deckeditor.components.lobbies.interfaces import LobbyViewInterface


class ReleaseSelector(QWidget):
    release_selected = pyqtSignal(int)

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self._lobby_view = lobby_view

        self._cube_selector = QtWidgets.QComboBox()
        self._release_selector = QtWidgets.QComboBox()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._cube_selector)
        layout.addWidget(self._release_selector)

        self.setLayout(layout)

        self._update()

        LOBBIES_CONTROLLER.versioned_cubes_changed.connect(self._update)
        self._cube_selector.activated.connect(self._on_cube_selected)
        self._release_selector.activated.connect(self._on_release_selected)

    def update_content(self, release_id: t.Union[str, int], enabled: bool) -> None:
        versioned_cube = LOBBIES_CONTROLLER.release_versioned_cube_map.get(release_id)
        if versioned_cube is None:
            return
        self._cube_selector.setCurrentIndex(
            LOBBIES_CONTROLLER.versioned_cubes.index(
                LOBBIES_CONTROLLER.release_versioned_cube_map[release_id]
            )
        )
        idx = 0
        self._release_selector.clear()
        for _idx, release in enumerate(versioned_cube.releases):
            self._release_selector.addItem(release.name, release.id)
            if release.id == release_id:
                idx = _idx

        self._release_selector.setCurrentIndex(idx)

        self._cube_selector.setEnabled(enabled)
        self._release_selector.setEnabled(enabled)

    def _update(self):
        self._cube_selector.clear()
        for versioned_cube in LOBBIES_CONTROLLER.versioned_cubes:
            self._cube_selector.addItem(versioned_cube.name, versioned_cube.id)

    def _on_release_selected(self, idx: int) -> None:
        self.release_selected.emit(self._release_selector.itemData(idx))

    def _on_cube_selected(self, idx: int) -> None:
        versioned_cube = LOBBIES_CONTROLLER.versioned_cubes[idx]
        if not self._release_selector.currentData() in (
            release.id
            for release in
            versioned_cube.releases
        ):
            self._release_selector.clear()
            for release in versioned_cube.releases:
                self._release_selector.addItem(release.name, release.id)

            self._release_selector.setCurrentIndex(0)

            self.release_selected.emit(self._release_selector.itemData(0))
