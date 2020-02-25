from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem

from frozendict import frozendict
from bidict import bidict

from cubeclient.models import VersionedCube
from lobbyclient.client import LobbyClient, Lobby

from deckeditor.context.context import Context


class _LobbyClient(LobbyClient):

    def __init__(self, model: LobbyModelClientConnection, url: str, token: str):
        super().__init__(url, token)
        self._model = model

    def _lobbies_changed(
        self,
        created: t.Mapping[str, Lobby] = frozendict(),
        modified: t.Mapping[str, Lobby] = frozendict(),
        closed: t.AbstractSet[str] = frozenset(),
    ) -> None:
        self._model.changed.emit()

    def _on_error(self, error):
        super()._on_error(error)
        self._model.on_disconnected()

    def _on_close(self):
        super()._on_close()

    def _game_started(self, lobby: Lobby, key: str) -> None:
        Context.sealed_started.emit(int(key))


class LobbyModelClientConnection(QObject):
    changed = pyqtSignal()
    connected = pyqtSignal(bool)

    def __init__(self, parent: t.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._lobby_client: t.Optional[LobbyClient] = None

        if Context.cube_api_client.token:
            self._logged_in(None)

        Context.token_changed.connect(self._logged_in)

    @property
    def is_connected(self) -> bool:
        return self._lobby_client is not None

    def on_disconnected(self):
        self._lobby_client = None
        self.connected.emit(False)
        self.changed.emit()

    def _logged_in(self, _):
        if self._lobby_client is not None:
            self._lobby_client.close()

        self._lobby_client = _LobbyClient(
            self,
            url = 'ws://' + Context.host + '/ws/lobbies/',
            token = Context.cube_api_client.token,
        )
        self.connected.emit(True)

    def get_lobbies(self) -> t.Mapping[str, Lobby]:
        if self._lobby_client is None:
            return {}
        return self._lobby_client.get_lobbies()

    def get_lobby(self, name: str) -> t.Optional[Lobby]:
        if self._lobby_client is None:
            return None
        return self._lobby_client.get_lobby(name)

    def create_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.create_lobby(name)

    def set_options(self, name: str, options: t.Any) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_options(name, options)

    def set_game_type(self, name: str, game_type: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_game_type(name, game_type)

    def leave_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.leave_lobby(name)

    def join_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.join_lobby(name)

    def set_ready(self, name: str, ready: bool) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_ready(name, ready)

    def start_game(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.start_game(name)


class LobbiesListView(QTableWidget):

    def __init__(self, parent: LobbiesView):
        super().__init__(0, 6, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'game_type', 'state', 'owner', 'users', 'size')
        )

        self._lobby_view = parent

        self._lobbies: t.List[Lobby] = []

        self._update_content()
        self._lobby_view.lobby_model.changed.connect(self._update_content)

        self.setEditTriggers(self.NoEditTriggers)

        self.cellDoubleClicked.connect(self._cell_double_clicked)

    def _cell_double_clicked(self, row: int, column: int) -> None:
        self._lobby_view.lobby_model.join_lobby(
            self._lobbies[row].name
        )

    def _update_content(self) -> None:
        def _set_data_at(data: str, _row: int, _column: int):
            _item = QTableWidgetItem()
            _item.setData(0, data)
            self.setItem(_row, _column, _item)

        self._lobbies = sorted(
            self._lobby_view.lobby_model.get_lobbies().values(),
            key = lambda l: l.name,
        )
        self.setRowCount(len(self._lobbies))

        for index, lobby in enumerate(self._lobbies):
            for column, value in enumerate(
                (
                    lobby.name,
                    lobby.game_type,
                    lobby.state,
                    lobby.owner,
                    str(len(lobby.users)),
                    str(lobby.size),
                )
            ):
                _set_data_at(value, index, column)

        self.resizeColumnsToContents()


class LobbyUserListView(QTableWidget):

    def __init__(self, lobby_model: LobbyModelClientConnection, lobby_name: str, parent: t.Optional[QObject] = None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'ready')
        )

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


class ReleaseSelector(QWidget):

    def __init__(self, lobby_view: LobbyView):
        super().__init__()
        self._lobby_view = lobby_view

        self._cube_selector = QtWidgets.QComboBox()
        self._release_selector = QtWidgets.QComboBox()

        layout = QtWidgets.QHBoxLayout()

        layout.addWidget(self._cube_selector)
        layout.addWidget(self._release_selector)

        self.setLayout(layout)

        self._versioned_cubes: t.List[VersionedCube] = []
        self._release_versioned_cube_map: t.Mapping[t.Union[str, int], VersionedCube] = {}

        self._update()

        self._cube_selector.activated.connect(self._on_cube_selected)
        self._release_selector.activated.connect(self._on_release_selected)

    def update_content(self, release_id: t.Union[str, int], enabled: bool) -> None:
        versioned_cube = self._release_versioned_cube_map[release_id]
        self._cube_selector.setCurrentIndex(
            self._versioned_cubes.index(
                self._release_versioned_cube_map[release_id]
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
        self._versioned_cubes = list(Context.cube_api_client.versioned_cubes())
        self._release_versioned_cube_map = {
            release.id: versioned_cube
            for versioned_cube in
            self._versioned_cubes
            for release in
            versioned_cube.releases
        }

        self._cube_selector.clear()
        for versioned_cube in self._versioned_cubes:
            self._cube_selector.addItem(versioned_cube.name, versioned_cube.id)

    def _on_release_selected(self, idx: int) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {'release': self._release_selector.itemData(idx)},
        )

    def _on_cube_selected(self, idx: int) -> None:
        versioned_cube = self._versioned_cubes[idx]
        if not self._release_selector.currentData() in (
            release.id
            for release in
            versioned_cube.releases
        ):
            self._release_selector.clear()
            for release in versioned_cube.releases:
                self._release_selector.addItem(release.name, release.id)

            self._release_selector.setCurrentIndex(0)

            self._lobby_view.lobby_model.set_options(
                self._lobby_view.lobby.name,
                {'release': self._release_selector.itemData(0)},
            )


class FormatSelector(QtWidgets.QComboBox):

    def __init__(self, lobby_view: LobbyView):
        super().__init__()
        self._lobby_view = lobby_view

        self.addItem('limited_sideboard')
        self.addItem('limited_15_sideboard')

        self.activated.connect(self._on_activated)

    def update_content(self, game_format: str, enabled: bool) -> None:
        self.setCurrentText(game_format)
        self.setEnabled(enabled)

    def _on_activated(self, idx: int) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {'format': self.itemText(idx)},
        )


class PoolSizeSelector(QtWidgets.QSpinBox):

    def __init__(self, lobby_view: LobbyView):
        super().__init__()
        self._lobby_view = lobby_view
        self.setRange(1, 180)
        self.valueChanged.connect(self._on_value_changed)

    def update_content(self, pool_size: int, enabled: bool) -> None:
        self.blockSignals(True)
        self.setValue(pool_size)
        self.blockSignals(False)
        self.setEnabled(enabled)

    def _on_value_changed(self, value: int) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {'pool_size': value},
        )


class OptionsSelector(QWidget):

    def __init__(self, lobby_view: LobbyView):
        super().__init__()
        self._lobby_view = lobby_view

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        pass


class SealedOptionsSelector(OptionsSelector):

    def __init__(self, lobby_view: LobbyView):
        super().__init__(lobby_view)

        self._release_selector = ReleaseSelector(lobby_view)
        self._format_selector = FormatSelector(lobby_view)
        self._pool_size_selector = PoolSizeSelector(lobby_view)

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._release_selector)
        layout.addWidget(self._format_selector)
        layout.addWidget(self._pool_size_selector)

        self.setLayout(layout)

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._release_selector.update_content(options['release'], enabled)
        self._format_selector.update_content(options['format'], enabled)
        self._pool_size_selector.update_content(options['pool_size'], enabled)


class DraftOptionsSelector(OptionsSelector):
    pass


class GameOptionsSelector(QtWidgets.QStackedWidget):

    def __init__(self, lobby_view: LobbyView):
        super().__init__()
        self._lobby_view = lobby_view

        self._options_selectors = {
            'draft': DraftOptionsSelector(lobby_view),
            'sealed': SealedOptionsSelector(lobby_view),
        }
        for option_selector in self._options_selectors.values():
            self.addWidget(option_selector)

    def update_content(self, game_type: str, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        options_selector = self._options_selectors[game_type]
        self.setCurrentWidget(options_selector)
        options_selector.update_content(options, enabled)


class LobbyView(QWidget):
    options_changed = pyqtSignal(dict)

    def __init__(self, lobby_model: LobbyModelClientConnection, lobby_name: str, parent: t.Optional[QObject] = None):
        super().__init__(parent)
        self._lobby_model = lobby_model
        self._lobby_name = lobby_name

        layout = QtWidgets.QVBoxLayout()

        self._ready_button = QtWidgets.QPushButton('ready')
        self._ready_button.clicked.connect(self._toggle_ready)

        self._start_game_button = QtWidgets.QPushButton('start')
        self._start_game_button.clicked.connect(self._start_game)

        self._game_type_selector = QtWidgets.QComboBox()
        self._game_type_selector.addItem('draft')
        self._game_type_selector.addItem('sealed')
        self._game_type_selector.activated.connect(self._on_game_type_selected)

        self._options_selector = GameOptionsSelector(self)

        # self._reconnect_button = QtWidgets.QPushButton('reconnect')
        # self._reconnect_button.clicked.connect(self._reconnect)

        users_list = LobbyUserListView(self._lobby_model, self._lobby_name)

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(self._ready_button)
        top_layout.addWidget(self._start_game_button)
        # top_layout.addWidget(self._reconnect_button)

        layout.addLayout(top_layout)
        layout.addWidget(self._game_type_selector)
        layout.addWidget(self._options_selector)
        layout.addWidget(users_list)

        self._update_content()
        self._lobby_model.changed.connect(self._update_content)

        self.setLayout(layout)

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
            self._lobby_model.set_game_type(self._lobby_name, self._game_type_selector.itemText(idx))

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

    # def _reconnect(self) -> None:
    #     lobby = self._lobby_model.get_lobby(self._lobby_name)
    #     if lobby.options.get('game_type') == 'sealed':
    #         sealed_pool = Context.cube_api_client.get_sealed_pool(
    #             lobby.key
    #         )
    #         Context.new_pool.emit(sealed_pool.pool)

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

        self._game_type_selector.setEnabled(can_edit_options)

        self._game_type_selector.setCurrentText(lobby.game_type)
        self._options_selector.update_content(lobby.game_type, lobby.options, can_edit_options)

        self._start_game_button.setVisible(
            lobby.state == 'pre-game'
            and Context.cube_api_client.user.username == lobby.owner
            and all(
                user.ready
                for user in
                lobby.users.values()
            )
        )


class CreateLobbyDialog(QtWidgets.QDialog):

    def __init__(self, parent: LobbiesView = None):
        super().__init__(parent)
        self._lobby_view = parent

        self._ok_button = QtWidgets.QPushButton('Ok', self)
        self._lobby_name_selector = QtWidgets.QLineEdit()

        self._top_box = QtWidgets.QHBoxLayout()
        self._bottom_box = QtWidgets.QHBoxLayout()

        self._top_box.addWidget(self._lobby_name_selector)

        self._bottom_box.addWidget(self._ok_button)

        self._layout = QtWidgets.QVBoxLayout()

        self._layout.addLayout(self._top_box)
        self._layout.addLayout(self._bottom_box)

        self.setLayout(self._layout)

        self._ok_button.clicked.connect(self._create)

        self._lobby_name_selector.setFocus()

    def _create(self) -> None:
        self._lobby_view.lobby_model.create_lobby(
            self._lobby_name_selector.text()
        )
        self.accept()


class LobbyTabs(QtWidgets.QTabWidget):

    def __init__(self, parent: LobbiesView):
        super().__init__(parent)
        self._lobby_view: LobbiesView = parent

        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self._tab_close_requested)
        self._lobby_view.lobby_model.changed.connect(self._update_content)

        self._tabs_map: bidict[str, int] = bidict()

    def _update_content(self) -> None:
        lobbies = {
            name: lobby
            for name, lobby in
            self._lobby_view.lobby_model.get_lobbies().items()
            if Context.cube_api_client.user.username in lobby.users
        }

        removed = self._tabs_map.keys() - lobbies.keys()
        if removed:
            for removed_name, removed_index in sorted(
                (
                    (name, self._tabs_map[name])
                    for name in
                    removed
                ),
                key = lambda kv: kv[1],
                reverse = True,
            ):
                del self._tabs_map[removed_name]

                for name, index in self._tabs_map.items():
                    if index > removed_index:
                        self._tabs_map[name] -= 1

                self.removeTab(removed_index)

        added = lobbies.keys() - self._tabs_map.keys()
        if added:
            max_index = max(self._tabs_map.values()) if self._tabs_map else -1
            for added_name in added:
                max_index += 1
                self._tabs_map[added_name] = max_index
                self.insertTab(
                    max_index,
                    LobbyView(self._lobby_view.lobby_model, added_name),
                    added_name,
                )

    def _tab_close_requested(self, index: int) -> None:
        self._lobby_view.lobby_model.leave_lobby(
            self._tabs_map.inverse[index]
        )


class LobbiesView(QWidget):
    lobbies_changed = pyqtSignal()

    def __init__(self, lobby_model: LobbyModelClientConnection, parent: t.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._lobby_model = lobby_model

        lobbies_list_view = LobbiesListView(self)

        self._lobby_tabs = LobbyTabs(self)

        layout = QtWidgets.QVBoxLayout()

        self._create_lobby_button = QtWidgets.QPushButton('Create lobby')
        self._create_lobby_button.clicked.connect(self._create_lobby)
        if not self._lobby_model.is_connected:
            self._create_lobby_button.setEnabled(False)
        self._lobby_model.connected.connect(self._on_connection_status_change)

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(lobbies_list_view)
        top_layout.addWidget(self._lobby_tabs)

        layout.addLayout(top_layout)
        layout.addWidget(self._create_lobby_button)

        self.setLayout(layout)

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
