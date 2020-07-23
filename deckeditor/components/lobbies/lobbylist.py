from __future__ import annotations

import typing as t

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

from lobbyclient.client import Lobby

from deckeditor.components.lobbies.interfaces import LobbiesViewInterface


class LobbiesListView(QTableWidget):

    def __init__(self, parent: LobbiesViewInterface):
        super().__init__(0, 8, parent)
        self.setHorizontalHeaderLabels(
            ('Name', 'Game Type', 'State', 'Owner', 'Users', 'Min Size', 'Req. Ready', 'Auto Unready')
        )

        self._lobby_view = parent

        self._lobbies: t.List[Lobby] = []

        self._update_content()
        self._lobby_view.lobby_model.changed.connect(self._update_content)

        self.setEditTriggers(self.NoEditTriggers)
        self.setFocusPolicy(Qt.ClickFocus)

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
                    '{}/{}'.format(
                        len(lobby.users),
                        lobby.lobby_options.size,
                    ),
                    str(lobby.lobby_options.minimum_size),
                    bool(lobby.lobby_options.require_ready),
                    bool(lobby.lobby_options.unready_on_change),
                )
            ):
                _set_data_at(value, index, column)

        self.resizeColumnsToContents()