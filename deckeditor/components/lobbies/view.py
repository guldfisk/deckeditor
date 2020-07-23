from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from lobbyclient.model import LobbyOptions

from deckeditor.components.lobbies.client import LobbyModelClientConnection
from deckeditor.components.lobbies.interfaces import LobbiesViewInterface
from deckeditor.components.lobbies.lobbylist import LobbiesListView
from deckeditor.components.lobbies.tabs import LobbyTabs
from deckeditor.store.models import GameTypeOptions, LobbyOptions as LobbyOptionsStore
from deckeditor.utils.actions import WithActions


class CreateLobbyDialog(QtWidgets.QDialog):

    def __init__(self, parent: LobbiesView = None):
        super().__init__(parent)
        self._lobby_view = parent

        self.setWindowTitle('Create Lobby')

        lobby_options = LobbyOptionsStore.get_options_for_name('default') or {}

        self._lobby_name_selector = QtWidgets.QLineEdit()

        self._game_type_selector = QtWidgets.QComboBox()
        self._game_type_selector.addItems(('sealed', 'draft'))
        self._game_type_selector.setCurrentText(lobby_options.get('game_type', 'draft'))

        self._size_selector_label = QtWidgets.QLabel('size')
        self._size_selector = QtWidgets.QSpinBox()
        self._size_selector.setMinimum(1)
        self._size_selector.setMaximum(64)
        self._size_selector.setValue(lobby_options.get('size', 8))

        self._min_size_selector_label = QtWidgets.QLabel('min size')
        self._min_size_selector = QtWidgets.QSpinBox()
        self._min_size_selector.setMinimum(0)
        self._min_size_selector.setMaximum(64)
        self._min_size_selector.setValue(lobby_options.get('minimum_size', 0))

        self._requires_ready_selector = QtWidgets.QCheckBox('require ready')
        self._requires_ready_selector.setChecked(lobby_options.get('require_ready', True))
        self._auto_unready_selector = QtWidgets.QCheckBox('auto unready')
        self._auto_unready_selector.setChecked(lobby_options.get('unready_on_change', True))

        self._ok_button = QtWidgets.QPushButton('OK', self)

        layout = QtWidgets.QGridLayout(self)

        layout.addWidget(self._lobby_name_selector, 0, 0, 1, 4)
        layout.addWidget(self._game_type_selector, 1, 0, 1, 4)
        layout.addWidget(self._size_selector_label, 2, 0, 1, 1)
        layout.addWidget(self._size_selector, 2, 1, 1, 1)
        layout.addWidget(self._min_size_selector_label, 2, 2, 1, 1)
        layout.addWidget(self._min_size_selector, 2, 3, 1, 1)
        layout.addWidget(self._requires_ready_selector, 3, 0, 1, 2)
        layout.addWidget(self._auto_unready_selector, 3, 2, 1, 2)
        layout.addWidget(self._ok_button, 4, 3, 1, 1)

        self._ok_button.clicked.connect(self._create)

        self._lobby_name_selector.setFocus()

    def _get_lobby_options(self) -> LobbyOptions:
        return LobbyOptions(
            size = self._size_selector.value(),
            minimum_size = self._min_size_selector.value(),
            require_ready = self._requires_ready_selector.isChecked(),
            unready_on_change = self._auto_unready_selector.isChecked(),
        )

    def _create(self) -> None:
        lobby_options = self._get_lobby_options()
        game_type = self._game_type_selector.currentText()

        LobbyOptionsStore.save_options(
            'default',
            {
                'game_type': game_type,
                **lobby_options.__dict__
            },
        )

        self._lobby_view.lobby_model.create_lobby(
            name = self._lobby_name_selector.text(),
            game_type = game_type,
            lobby_options = lobby_options,
            game_options = GameTypeOptions.get_options_for_game_type(game_type) or {},
        )

        self.accept()


class LobbiesView(LobbiesViewInterface, WithActions):
    lobbies_changed = pyqtSignal()

    def __init__(self, lobby_model: LobbyModelClientConnection, parent: t.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._lobby_model = lobby_model

        lobbies_list_view = LobbiesListView(self)

        self._lobby_tabs = LobbyTabs(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)

        self._create_lobby_button = QtWidgets.QPushButton('Create lobby')
        self._create_lobby_button.clicked.connect(self._create_lobby)
        if not self._lobby_model.is_connected:
            self._create_lobby_button.setEnabled(False)
        self._lobby_model.connected.connect(self._on_connection_status_change)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        splitter.addWidget(lobbies_list_view)
        splitter.addWidget(self._lobby_tabs)
        splitter.setCollapsible(1, False)

        layout.addWidget(splitter)
        layout.addWidget(self._create_lobby_button)

        self._create_action('Create Lobby', self._create_lobby, 'N')

    def _on_connection_status_change(self, connected: bool) -> None:
        self._create_lobby_button.setEnabled(connected)

    @property
    def lobby_model(self) -> LobbyModelClientConnection:
        return self._lobby_model

    def set_model(self, lobby_model: LobbyModelClientConnection) -> None:
        self._lobby_model = lobby_model
        self.lobbies_changed.connect(lobby_model.changed)

    def _create_lobby(self) -> None:
        dialog = CreateLobbyDialog(self)
        dialog.exec()
