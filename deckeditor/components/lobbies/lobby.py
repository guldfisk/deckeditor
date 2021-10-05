from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QTableWidget, QAbstractItemView, QTableWidgetItem

from lobbyclient.client import Lobby

from deckeditor.components.lobbies.client import LobbyModelClientConnection
from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.gameoptions import GameOptionsSelector
from deckeditor.context.context import Context
from deckeditor.store.models import GameTypeOptions
from deckeditor.utils.scroll import VerticalScrollArea


class LobbyUserListView(QTableWidget):

    def __init__(self, lobby_model: LobbyModelClientConnection, lobby_name: str, parent: t.Optional[QObject] = None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'ready')
        )
        self.setMaximumWidth(350)
        self.setMinimumWidth(200)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._lobby_model = lobby_model
        self._lobby_name = lobby_name

        self._update_content()
        self._lobby_model.changed.connect(self._update_content)

        self.resizeColumnsToContents()

    def _update_content(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)

        users = () if lobby is None else lobby.users.values()
        self.setRowCount(len(users))

        for index, user in enumerate(sorted(users, key = lambda u: u.username)):
            item = QTableWidgetItem()
            item.setData(0, user.username)
            self.setItem(index, 0, item)

            item = QTableWidgetItem()
            item.setData(0, 'ready' if user.ready else 'unready')
            self.setItem(index, 1, item)


class LobbyView(LobbyViewInterface):
    options_changed = pyqtSignal(dict)

    def __init__(self, lobby_model: LobbyModelClientConnection, lobby_name: str, parent: t.Optional[QObject] = None):
        super().__init__(parent)
        self._lobby_model = lobby_model
        self._lobby_name = lobby_name

        layout = QtWidgets.QGridLayout(self)

        self._ready_button = QtWidgets.QPushButton('ready')
        self._ready_button.clicked.connect(self._toggle_ready)

        self._start_game_button = QtWidgets.QPushButton('start')
        self._start_game_button.clicked.connect(self._start_game)

        self._game_type_selector = QtWidgets.QComboBox()
        self._game_type_selector.addItem('draft')
        self._game_type_selector.addItem('sealed')
        self._game_type_selector.activated.connect(self._on_game_type_selected)

        self._options_selector = GameOptionsSelector(self)
        self._options_selector_area = VerticalScrollArea()
        self._options_selector_area.setMinimumHeight(350)
        self._options_selector_area.setWidget(self._options_selector)

        self._reconnect_button = QtWidgets.QPushButton('reconnect')
        self._reconnect_button.clicked.connect(self._reconnect)

        users_list = LobbyUserListView(self._lobby_model, self._lobby_name)

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(self._ready_button)
        top_layout.addWidget(self._start_game_button)
        top_layout.addWidget(self._reconnect_button)

        layout.addLayout(top_layout, 0, 0, 1, 3)
        layout.addWidget(self._game_type_selector, 1, 0, 1, 2)
        layout.addWidget(self._options_selector_area, 2, 0, 1, 2)
        layout.addWidget(users_list, 1, 2, 2, 1)

        self._update_content()
        self._lobby_model.changed.connect(self._update_content)

    @property
    def lobby(self) -> t.Optional[Lobby]:
        return self._lobby_model.get_lobby(self._lobby_name)

    @property
    def lobby_model(self) -> LobbyModelClientConnection:
        return self._lobby_model

    def _on_game_type_selected(self, idx: int) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if lobby is None:
            return

        user = lobby.users.get(Context.cube_api_client.user.username)
        if user and user.username == lobby.owner:
            game_type = self._game_type_selector.itemText(idx)

            self._lobby_model.set_game_type(
                self._lobby_name,
                game_type,
                GameTypeOptions.get_options_for_game_type(game_type) or {},
            )

    def _toggle_ready(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if lobby:
            user = lobby.users.get(Context.cube_api_client.user.username)
            if user is not None:
                self._lobby_model.set_ready(
                    self._lobby_name,
                    not user.ready,
                )

    def _start_game(self) -> None:
        self._lobby_model.start_game(self._lobby_name)

    def _reconnect(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if lobby.game_type == 'draft':
            Context.draft_started.emit(lobby.key)

    def _update_content(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if not lobby:
            return

        user = lobby.users.get(Context.cube_api_client.user.username)
        if user is None:
            return

        can_edit_options = Context.cube_api_client.user.username == lobby.owner and lobby.state == 'pre-game'

        self._ready_button.setText(
            'unready' if user.ready else 'ready'
        )
        self._ready_button.setVisible(lobby.state == 'pre-game')

        self._reconnect_button.setVisible(lobby.state == 'game')

        self._game_type_selector.setEnabled(can_edit_options)

        self._game_type_selector.setCurrentText(lobby.game_type)
        self._options_selector.update_content(lobby.game_type, lobby.game_options, can_edit_options)

        self._start_game_button.setVisible(
            lobby.state == 'pre-game'
            and Context.cube_api_client.user.username == lobby.owner
            and len(lobby.users) >= lobby.lobby_options.minimum_size
            and (
                not lobby.lobby_options.require_ready
                or all(
                    user.ready
                    for user in
                    lobby.users.values()
                )
            )
        )
