from __future__ import annotations

import typing
import typing as t
from abc import abstractmethod

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem

from frozendict import frozendict
from bidict import bidict

from deckeditor.context.context import Context

from lobbyclient.client import LobbyClient, Lobby


class _LobbyClient(LobbyClient):

    def __init__(self, model: LobbyModel, url: str, token: str):
        super().__init__(url, token)
        self._model = model

    def _lobbies_changed(
        self,
        created: t.Mapping[str, Lobby] = frozendict(),
        modified: t.Mapping[str, Lobby] = frozendict(),
        closed: t.AbstractSet[str] = frozenset(),
    ) -> None:
        print('lobbies changed', created, modified, closed)
        self._model.changed.emit()


class LobbyModel(QObject):
    changed = pyqtSignal()

    @abstractmethod
    def get_lobbies(self) -> t.Mapping[str, Lobby]:
        pass

    @abstractmethod
    def get_lobby(self, name: str) -> t.Optional[Lobby]:
        pass

    @abstractmethod
    def create_lobby(self, name: str) -> None:
        pass


class LobbyModelClientConnection(LobbyModel):
    changed = pyqtSignal()
    connected = pyqtSignal(bool)

    def __init__(self, parent: typing.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._lobby_client: t.Optional[LobbyClient] = None
        if Context.token:
            self._logged_in(None)
        Context.token_changed.connect(self._logged_in)

    @property
    def is_connected(self) -> bool:
        return self._lobby_client is not None

    def _logged_in(self, _):
        if self._lobby_client is not None:
            self._lobby_client.close()
        self._lobby_client = _LobbyClient(
            self,
            url = 'ws://' + Context.host + '/ws/lobbies/',
            token = Context.token,
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

    def leave_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.leave_lobby(name)

    def join_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.join_lobby(name)


class DummyLobbyModel(LobbyModel):

    def get_lobbies(self) -> t.Mapping[str, Lobby]:
        return {}

    def get_lobby(self, name: str) -> t.Optional[Lobby]:
        return None

    def create_lobby(self, name: str) -> None:
        pass


class LobbiesListView(QTableWidget):

    def __init__(self, parent: LobbyView):
        super().__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'owner', 'users', 'size')
        )

        self._lobby_view = parent

        self._lobbies: t.List[Lobby] = []

        self._update_content()
        self._lobby_view.lobby_model.changed.connect(self._update_content)

        self.resizeColumnsToContents()
        self.setEditTriggers(self.NoEditTriggers)

        self.cellDoubleClicked.connect(self._cell_double_clicked)
        # self.setSortingEnabled(True)

    def _cell_double_clicked(self, row: int, column: int) -> None:
        self._lobby_view.lobby_model.join_lobby(
            self._lobbies[row].name
        )

    def _update_content(self ) -> None:
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
            item.setData(0, lobby.owner)
            self.setItem(index, 1, item)

            item = QTableWidgetItem()
            item.setData(0, str(len(lobby.users)))
            self.setItem(index, 2, item)

            item = QTableWidgetItem()
            item.setData(0, str(lobby.size))
            self.setItem(index, 3, item)


class LobbyUserListView(QTableWidget):

    def __init__(self, lobby_model: LobbyModelClientConnection, lobby_name: str, parent: t.Optional[QObject] = None):
        super().__init__(0, 1, parent)
        self.setHorizontalHeaderLabels(
            ('name',)
        )

        self._lobby_model = lobby_model
        self._lobby_name = lobby_name

        self._update_content()
        self._lobby_model.changed.connect(self._update_content)

        self.resizeColumnsToContents()
        # self.setSortingEnabled(True)

    def _update_content(self ) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)

        users = () if lobby is None else lobby.users
        self.setRowCount(len(users))

        for index, user in enumerate(sorted(users)):
            item = QTableWidgetItem()
            item.setData(0, user)
            self.setItem(index, 0, item)


class CreateLobbyDialog(QtWidgets.QDialog):

    def __init__(self, parent: LobbyView = None):
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

    def _create(self) -> None:
        self._lobby_view.lobby_model.create_lobby(
            self._lobby_name_selector.text()
        )
        self.accept()


class LobbyTabs(QtWidgets.QTabWidget):

    def __init__(self, parent: LobbyView):
        super().__init__(parent)
        self._lobby_view: LobbyView = parent

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
                    LobbyUserListView(self._lobby_view.lobby_model, added_name),
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


class LobbyView(QWidget):
    lobbies_changed = pyqtSignal()

    def __init__(self, lobby_model: LobbyModelClientConnection, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._lobby_model = lobby_model

        lobbies_list_view = LobbiesListView(self)

        self._lobby_tabs = LobbyTabs(self)

        layout = QtWidgets.QVBoxLayout()

        self._create_lobby_button = QtWidgets.QPushButton('Create lobby')
        self._create_lobby_button.clicked.connect(self._create_lobby)
        print('lobbies connected?', self._lobby_model.is_connected)
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
        print('connected status change', connected)
        self._create_lobby_button.setEnabled(connected)

    @property
    def lobby_model(self) -> LobbyModelClientConnection:
        return self._lobby_model

    def set_model(self, lobby_model: LobbyModel) -> None:
        self._lobby_model = lobby_model
        self.lobbies_changed.connect(lobby_model.changed)

    def _create_lobby(self) -> None:
        dialog = CreateLobbyDialog(self)
        dialog.exec()
