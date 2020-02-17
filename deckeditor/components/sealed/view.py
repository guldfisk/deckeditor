from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QAbstractItemView

from cubeclient.models import SealedSession
from deckeditor.context.context import Context


class SessionsList(QTableWidget):

    def __init__(self, parent: SealedSessionsView):
        super().__init__(0, 5, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'format', 'release', 'players', 'pool size', 'created')
        )
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._sessions_view = parent

        self._sessions: t.List[SealedSession] = []

        self.cellDoubleClicked.connect(self._cell_double_clicked)

        self._update_content()
        Context.token_changed.connect(self._update_content)

    def _cell_double_clicked(self, row: int, column: int) -> None:
        print('double clicked', self._sessions[row].name)

    def _update_content(self, *args, **kwargs) -> None:
        if Context.cube_api_client.user is None:
            return

        def _set_data_at(data: str, _row: int, _column: int):
            item = QTableWidgetItem()
            item.setData(0, data)
            self.setItem(_row, _column, item)

        self._sessions = list(
            Context.cube_api_client.sealed_sessions(
                limit = 20,
                filters = {
                    'state_filter': 'DECK_BUILDING',
                    'players_filter': Context.cube_api_client.user.username,
                },
            )
        )

        self.setRowCount(len(self._sessions))

        for row, session in enumerate(self._sessions):
            for column, value in enumerate(
                (
                    session.name,
                    session.game_format,
                    session.release['name'],
                    ', '.join(sorted(player.username for player in session.players)),
                    session.pool_size,
                    str(session.created_at),
                )
            ):
                _set_data_at(value, row, column)

        self.resizeColumnsToContents()


class SealedSessionView(QWidget):

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QBoxLayout(self)


class SealedSessionsView(QWidget):
    # lobbies_changed = pyqtSignal()

    def __init__(self, parent: t.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._sessions_list = SessionsList(self)

        layout = QtWidgets.QHBoxLayout()

        layout.addWidget(self._sessions_list)

        self.setLayout(layout)

    def _get_sessions(self) -> None:
        Context.cube_api_client.sealed_sessions()
