from __future__ import annotations

import itertools
import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem

from frozendict import frozendict
from bidict import bidict

from cubeclient.models import VersionedCube
from deckeditor.components.draft.view import DraftModel
from deckeditor.context.context import Context

from lobbyclient.client import LobbyClient, Lobby


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
        self._model.on_disconnected()

    def _game_started(self, lobby: Lobby, key: str) -> None:
        if lobby.options['game_type'] == 'draft':
            Context.draft_started.emit(
                DraftModel(
                    key,
                    lobby.name,
                )
            )
        else:
            sealed_pool = Context.cube_api_client.get_sealed_pool(
                lobby.key
            )
            Context.new_pool.emit(sealed_pool.pool)


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

    # def get_options(self, name: str) -> t.Any:
    #     if self._lobby_client is None:
    #         return
    #     return self._lobby_client.get_lobby(name)

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
        super().__init__(0, 5, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'state', 'owner', 'users', 'size')
        )

        self._lobby_view = parent

        self._lobbies: t.List[Lobby] = []

        self._update_content()
        self._lobby_view.lobby_model.changed.connect(self._update_content)

        self.setEditTriggers(self.NoEditTriggers)

        self.cellDoubleClicked.connect(self._cell_double_clicked)
        # self.setSortingEnabled(True)

    def _cell_double_clicked(self, row: int, column: int) -> None:
        self._lobby_view.lobby_model.join_lobby(
            self._lobbies[row].name
        )

    def _update_content(self) -> None:
        self._lobbies = sorted(
            self._lobby_view.lobby_model.get_lobbies().values(),
            key = lambda l: l.name,
        )

        self.setRowCount(len(self._lobbies))

        for index, lobby in enumerate(self._lobbies):
            item = QTableWidgetItem()
            item.setData(0, lobby.name)
            self.setItem(index, 0, item)

            item = QTableWidgetItem()
            item.setData(0, lobby.state)
            self.setItem(index, 1, item)

            item = QTableWidgetItem()
            item.setData(0, lobby.owner)
            self.setItem(index, 2, item)

            item = QTableWidgetItem()
            item.setData(0, str(len(lobby.users)))
            self.setItem(index, 3, item)

            item = QTableWidgetItem()
            item.setData(0, str(lobby.size))
            self.setItem(index, 4, item)

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
        # self.setSortingEnabled(True)

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

    def __init__(self):
        super().__init__()
        self._cube_selector = QtWidgets.QComboBox()
        self._release_selector = QtWidgets.QComboBox()

        layout = QtWidgets.QHBoxLayout()

        layout.addWidget(self._cube_selector)
        layout.addWidget(self._release_selector)

        self.setLayout(layout)

        self._versioned_cubes: t.List[VersionedCube] = []
        self._release_versioned_cube_map: t.Mapping[t.Union[str, int], VersionedCube] = {}

        self._update()

        self._cube_selector.currentIndexChanged(self._on_cube_selected)

    def set_release(self, release_id: t.Union[str, int]) -> None:
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

    def _on_cube_selected(self, versioned_cube: VersionedCube) -> None:
        print(versioned_cube)
        # self._release_selector.clear()
        # for release in versioned_cube.releases:
        #     self._release_selector.addItem(release.name, release.id)

    # def release(self) -> t.Union[str, int]:
    #     return 14


class OptionsSelector(QWidget):
    # changed = pyqtSignal()

    def __init__(self, lobby_view: LobbyView):
        super().__init__()
        self._lobby_view = lobby_view

    def set_options(self, options: t.Mapping[str, t.Any]) -> None:
        pass

    # def _on_changed(self) -> None:
    #     self._lobby_view.options_changed.emit(self.options())
    #
    # def options(self) -> t.Mapping[str, t.Any]:
    #     pass


class SealedOptionsSelector(OptionsSelector):

    def __init__(self, lobby_view: LobbyView):
        super().__init__(lobby_view)

        self._release_selector = ReleaseSelector()

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._release_selector)

        self.setLayout(layout)

    def set_options(self, options: t.Mapping[str, t.Any]) -> None:
        self._release_selector.set_release(options['release'])

    # def options(self) -> t.Mapping[str, t.Any]:
    #     return {
    #         'relase': self._release_selector.release(),
    #         'pool_size': 90,
    #         'format': 'limited_sideboard',
    #         'game_type': 'sealed'
    #     }


class DraftOptionsSelector(OptionsSelector):
    pass
    # def options(self) -> t.Mapping[str, t.Any]:
    #     return {
    #         'game_type': 'sealed'
    #     }


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

        # self.setCurrentWidget(self._options_selectors[self._lobby_view.])

    # def _on_options_changed(self, options: t.Mapping[str, t.Any]) -> None:
    #     self.setCurrentWidget(self._options_selectors[options['game_type']])


class LobbyView(QWidget):
    options_changed = pyqtSignal(dict)

    def __init__(self, lobby_model: LobbyModelClientConnection, lobby_name: str, parent: t.Optional[QObject] = None):
        super().__init__(parent)
        self._lobby_model = lobby_model
        self._lobby_name = lobby_name

        layout = QtWidgets.QVBoxLayout()

        self._ready_button = QtWidgets.QPushButton('ready')
        self._ready_button.clicked.connect(self._toggle_ready)

        self._start_game_button = QtWidgets.QPushButton('start draft')
        self._start_game_button.clicked.connect(self._start_game)

        self._game_type_selector = QtWidgets.QComboBox()
        self._game_type_selector.addItem('draft')
        self._game_type_selector.addItem('sealed')
        self._game_type_selector.currentTextChanged.connect(self._select_game_type)

        self._options_selector = QtWidgets.QStackedWidget()


        # self._reconnect_button = QtWidgets.QPushButton('reconnect')
        # self._reconnect_button.clicked.connect(self._reconnect)

        users_list = LobbyUserListView(self._lobby_model, self._lobby_name)

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(self._ready_button)
        top_layout.addWidget(self._start_game_button)
        top_layout.addWidget(self._reconnect_button)

        layout.addLayout(top_layout)
        layout.addWidget(self._game_type_selector)
        layout.addWidget(users_list)

        self._update_content()
        self._lobby_model.changed.connect(self._update_content)

        self.setLayout(layout)

    def _select_game_type(self, game_type: str) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if lobby:
            user = lobby.users.get(Context.username)
            if user and user.username == lobby.owner:
                self._lobby_model.set_options(self._lobby_name, {'game_type': game_type})

    def _toggle_ready(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if lobby:
            user = lobby.users.get(Context.username)
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
        if lobby:
            game_type = lobby.options.get('game_type')
            self._game_type_selector.currentTextChanged.disconnect(self._select_game_type)
            if game_type is not None:
                self._game_type_selector.setCurrentText(game_type)
            self._game_type_selector.currentTextChanged.connect(self._select_game_type)

            user = lobby.users.get(Context.username)
            if user is not None:
                self._ready_button.setText(
                    'unready' if user.ready else 'ready'
                )
                self._ready_button.setVisible(lobby.state == 'pre-game')

                self._game_type_selector.setEnabled(
                    Context.username == lobby.owner
                )

                self._start_game_button.setVisible(
                    lobby.state == 'pre-game'
                    and Context.username == lobby.owner
                    and all(
                        user.ready
                        for user in
                        lobby.users.values()
                    )
                )

                self._reconnect_button.setVisible(
                    lobby.key is not None
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
        # self.setTabOrder(self._lobby_name_selector, self._ok_button)

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

        # self.currentChanged.connect(self._current_changed)

    def _update_content(self) -> None:
        lobbies = {
            name: lobby
            for name, lobby in
            self._lobby_view.lobby_model.get_lobbies().items()
            if Context.username in lobby.users
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

        # lobbies = sorted(
        #
        #     key = lambda l: l.name,
        # )
        # username = Context.username

    # def add_deck(self, deck: DeckView) -> None:
    #     self.addTab(deck, 'a deck')
    #
    # def new_deck(self, model: DeckModel) -> DeckView:
    #     deck_widget = DeckView(model)
    #     self.add_deck(
    #         deck_widget
    #     )
    #     self._new_decks += 1
    #
    #     return deck_widget

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
        self._lobby_model.connected.connect(self._connection_status_change)

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(lobbies_list_view)
        top_layout.addWidget(self._lobby_tabs)

        layout.addLayout(top_layout)
        layout.addWidget(self._create_lobby_button)

        self.setLayout(layout)

    def _connection_status_change(self, connected: bool) -> None:
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
