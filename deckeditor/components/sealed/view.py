from __future__ import annotations

import logging
import typing as t

import requests
import simplejson
from promise import promise

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QInputDialog, QHeaderView

from cubeclient.models import LimitedSession, LimitedDeck, LimitedPool

from deckeditor.components.views.editables.deck import DeckView
from deckeditor.context.context import Context


class SessionsList(QTableWidget):

    def __init__(self, parent: LimitedSessionsView):
        super().__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'format', 'players', 'created')
        )
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.verticalHeader().hide()
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self._sessions_view = parent

        self._sessions: t.Sequence[LimitedSession] = []

        self.cellDoubleClicked.connect(self._cell_double_clicked)

    def _cell_double_clicked(self, row: int, column: int) -> None:
        self._sessions_view.session_selected.emit(self._sessions[row])

    def set_sessions(self, sessions: t.Sequence[LimitedSession]) -> None:
        self._sessions = sessions

        def _set_data_at(data: str, _row: int, _column: int):
            item = QTableWidgetItem()
            item.setData(0, data)
            self.setItem(_row, _column, item)

        self.setRowCount(len(self._sessions))

        for row, session in enumerate(self._sessions):
            for column, value in enumerate(
                (
                    session.name,
                    session.game_format,
                    ', '.join(sorted(player.username for player in session.players)),
                    str(session.created_at),
                )
            ):
                _set_data_at(value, row, column)

        self.resizeColumnsToContents()


class DeckList(QTableWidget):

    def __init__(self, decks: t.Optional[t.List[LimitedDeck]] = None):
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels(
            ('name', 'created')
        )
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._decks: t.Sequence[LimitedDeck] = [] if decks is None else decks

        self._update_content()

    def set_decks(self, decks: t.Sequence[LimitedDeck]) -> None:
        self._decks = decks
        self._update_content()

    def _update_content(self) -> None:
        def _set_data_at(data: str, _row: int, _column: int):
            item = QTableWidgetItem()
            item.setData(0, data)
            self.setItem(_row, _column, item)

        self.setRowCount(len(self._decks))

        for row, deck in enumerate(self._decks):
            _set_data_at(deck.name, row, 0)
            _set_data_at(str(deck.created_at), row, 1)

        self.resizeColumnsToContents()


class LimitedSessionView(QWidget):

    def __init__(self, parent: LimitedSessionsView, session: t.Optional[LimitedSession] = None):
        super().__init__(parent)

        self._limited_sessions_view = parent
        self._session = session

        self._name_label = QtWidgets.QLabel()
        self._deck_list = DeckList()
        self._view_button = QtWidgets.QPushButton('View')
        self._submit_button = QtWidgets.QPushButton('Submit')

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._name_label)
        layout.addWidget(self._view_button)
        layout.addWidget(self._submit_button)
        layout.addWidget(self._deck_list)

        self.setLayout(layout)

        if self._session is not None:
            self._update_content()

        self._limited_sessions_view.session_selected.connect(self.set_session)
        self._view_button.clicked.connect(self._on_view)
        self._submit_button.clicked.connect(self._on_submit)

    @property
    def session(self) -> t.Optional[LimitedSession]:
        return self._session

    def _on_view(self):
        if not self._session:
            return
        for pool in self._session.pools:
            if pool.user == Context.cube_api_client.user:
                Context.new_pool.emit(pool.pool, pool.session.infinites, self._session.name)
                break

    def _on_upload_success(self, _) -> None:
        Context.notification_message.emit('Deck submitted')
        self._limited_sessions_view.update.emit()
        Context.cube_api_client.limited_session(self._session.id).then(self.set_session).catch(logging.warning)

    def _on_upload_error(self, error: Exception) -> None:
        if isinstance(error, ConnectionError):
            Context.notification_message.emit('disconnected')
        elif isinstance(error, requests.HTTPError):
            try:
                message = '\n'.join(
                    error.response.json()['errors']
                )
            except simplejson.errors.JSONDecodeError:
                message = 'Cannot upload deck'
            Context.notification_message.emit(message)

    def _on_submit(self):
        editable = Context.editor.current_editable()

        if isinstance(editable, DeckView):
            deck = editable.deck_model.as_deck().as_primitive_deck()

        else:
            deck = editable.pool_model.as_deck().as_primitive_deck()

        player_pool: t.Optional[LimitedPool] = None

        for pool in self._session.pools:
            if pool.user == Context.cube_api_client.user:
                player_pool = pool
                break

        if player_pool is None:
            return

        deck_name, success = QInputDialog.getText(
            self,
            'Submit Deck',
            (
                'Deck name'
                + '. Session is not in deck building state. This is, in fact, C H E A T I N G.'
                if (
                    self._session.state != LimitedSession.SealedSessionState.DECK_BUILDING
                    or player_pool.decks and self._session.open_decks
                ) else
                ''
            ),
            text = 'deck',
        )

        if not success:
            return

        Context.cube_api_client.upload_limited_deck(
            pool_id = player_pool.id,
            name = deck_name,
            deck = deck,
        ).then(
            self._on_upload_success
        ).catch(
            self._on_upload_error
        )

    def set_session(self, session: LimitedSession) -> None:
        self.show()
        self._session = session
        self._update_content()

    def _update_content(self) -> None:
        self._name_label.setText(self._session.name)
        for pool in self._session.pools:
            if pool.user == Context.cube_api_client.user:
                self._deck_list.set_decks(list(reversed(pool.decks)))
                break


class LimitedSessionsView(QWidget):
    session_selected = pyqtSignal(LimitedSession)
    update = pyqtSignal()

    def __init__(self, parent: t.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._sessions_list = SessionsList(self)
        self._limited_session_view = LimitedSessionView(self)
        self.setFocusProxy(self._sessions_list)

        self._limited_session_view.hide()

        layout = QtWidgets.QHBoxLayout()

        layout.addWidget(self._sessions_list)
        layout.addWidget(self._limited_session_view)

        self.setLayout(layout)

        Context.token_changed.connect(self.update)
        Context.sealed_started.connect(self._on_sealed_started)
        self.update.connect(self._on_update)

    def set_sessions(self, sessions: t.Sequence[LimitedSession]) -> t.Sequence[LimitedSession]:
        self._sessions_list.set_sessions(sessions)
        if not self._limited_session_view.session in sessions:
            self._limited_session_view.hide()

        return sessions

    def _on_sealed_started(self, pool_id, open_tab) -> None:
        if open_tab:
            def _after_sessions_updated(sessions: t.Sequence[LimitedSession]) -> None:
                found = False
                for session in sessions:
                    for pool in session.pools:
                        if pool.id == pool_id:
                            Context.new_pool.emit(pool.pool, pool.session.infinites, session.name)
                            found = True
                            break
                    if found:
                        break

            self._on_update().then(
                _after_sessions_updated
            )
        else:
            self._on_update()

    def _on_update(self) -> promise.Promise[t.Sequence[LimitedSession]]:
        if Context.cube_api_client.user is None:
            self.set_sessions(())
            return promise.Promise.resolve([])

        return Context.cube_api_client.limited_sessions(
            limit = 20,
            filters = {
                'state_filter': ['DECK_BUILDING', 'PLAYING'],
                'players_filter': Context.cube_api_client.user.username,
            },
        ).then(
            self.set_sessions
        )
