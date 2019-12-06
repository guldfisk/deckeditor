from __future__ import annotations

import typing
import typing as t
from abc import abstractmethod

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem
from frozendict import frozendict

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

    def __init__(self, parent: typing.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._lobby_client = _LobbyClient(
            self,
            url = 'ws://localhost:7000/ws/lobbies/',
            token = 'b43bc17f5119d7b1f7180ec073df462a4c7c0e5d06a42b34f0237d3921ff4e78',
        )

    def get_lobbies(self) -> t.Mapping[str, Lobby]:
        return self._lobby_client.get_lobbies()

    def get_lobby(self, name: str) -> t.Optional[Lobby]:
        return self._lobby_client.get_lobby(name)

    def create_lobby(self, name: str) -> None:
        self._lobby_client.create_lobby(name)


class DummyLobbyModel(LobbyModel):

    def get_lobbies(self) -> t.Mapping[str, Lobby]:
        return {}

    def get_lobby(self, name: str) -> t.Optional[Lobby]:
        return None

    def create_lobby(self, name: str) -> None:
        pass


class LobbiesListView(QTableWidget):

    def __init__(self, parent: LobbyModel):
        super().__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'owner', 'users', 'size')
        )

        self._lobby_model = lobby_model

        self._update_content()
        self._lobby_model.changed.connect(self._update_content)

        self.resizeColumnsToContents()
        # self.setSortingEnabled(True)

    def _update_content(self ) -> None:
        lobbies = self._lobby_model.get_lobbies()

        self.setRowCount(len(lobbies.values()))

        for index, lobby in enumerate(
            sorted(
                lobbies.values(),
                key = lambda l: l.name,
            )
        ):
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


# class LobbyUserListView(QTableWidget):
#
#     def __init__(self, lobby_name: str, parent: t.Optional[QObject] = None):
#         super().__init__(0, 1, parent)
#         self.setHorizontalHeaderLabels(
#             ('name',)
#         )
#
#         self._lobby_model = lobby_model
#         self._lobby_name = lobby_name
#
#         self._update_content()
#         self._lobby_model.changed.connect(self._update_content)
#
#         self.resizeColumnsToContents()
#         # self.setSortingEnabled(True)
#
#     def _update_content(self ) -> None:
#         lobby = self._lobby_model.get_lobby(self._lobby_name)
#
#         users = () if lobby is None else lobby.users
#         self.setRowCount(len(users))
#
#         for index, user in enumerate(sorted(users)):
#             item = QTableWidgetItem()
#             item.setData(0, user)
#             self.setItem(index, 0, item)


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


# class LobbyTabs(QtWidgets.QTabWidget):
#
#     def __init__(self, lobby_model: LobbyModel, user_name: str, parent: QtWidgets.QWidget = None):
#         super().__init__(parent)
#         self._lobby_model = lobby_model
#
#         self.setTabsClosable(True)
#
#         self._name_to_index_map: t.MutableMapping[str, int] = {}
#
#         self.tabCloseRequested.connect(self._tab_close_requested)
#         self._lobby_model.changed.connect(self._update_content)
#
#         # self.currentChanged.connect(self._current_changed)
#
#     def _update_content(self) -> None:
#         lobbies = self._lobby_model.client.lobbies
#
#         joined_lobbies
#
#     def add_deck(self, deck: DeckView) -> None:
#         self.addTab(deck, 'a deck')
#
#     def new_deck(self, model: DeckModel) -> DeckView:
#         deck_widget = DeckView(model)
#         self.add_deck(
#             deck_widget
#         )
#         self._new_decks += 1
#
#         return deck_widget
#
#     def _tab_close_requested(self, index: int) -> None:
#         self.removeTab(index)


class LobbyView(QWidget):

    def __init__(self, lobby_model: LobbyModel, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._lobby_model = lobby_model

        lobbies_list_view = LobbiesListView(self._lobby_model)
        layout = QtWidgets.QVBoxLayout()

        create_lobby_button = QtWidgets.QPushButton('Create lobby')
        create_lobby_button.clicked.connect(self._create_lobby)

        layout.addWidget(lobbies_list_view)
        layout.addWidget(create_lobby_button)

        self.setLayout(layout)

    @property
    def lobby_model(self) -> LobbyModel:
        return self._lobby_model

    def set_model(self, lobby_model: LobbyModel) -> None:


    def _create_lobby(self) -> None:
        dialog = CreateLobbyDialog(self._lobby_model, self)
        dialog.exec()
