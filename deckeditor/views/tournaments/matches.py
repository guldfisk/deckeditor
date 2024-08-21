from __future__ import annotations

import typing as t

from cubeclient.models import LimitedDeck, ScheduledMatch, TournamentParticipant
from hardcandy import fields
from hardcandy.schema import Schema
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal

from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.components.views.editables.deck import DeckView
from deckeditor.context.context import Context
from deckeditor.controllers.matches import MATCHES_CONTROLLER
from deckeditor.models.cubes.scenecard import SceneCard
from deckeditor.models.deck import DeckModel
from deckeditor.models.listtable import ListTableModel
from deckeditor.models.tournaments.matches import MatchSchema
from deckeditor.views.generic.readonlylisttable import ReadOnlyListTableView


class ParticipantsSchema(Schema):
    player = fields.Lambda(lambda p: p.player.username if p.player else "")
    deck = fields.Lambda(lambda p: p.deck.name)
    seed = fields.Float(max_precision=3)


class ScheduledMatchView(QtWidgets.QWidget):
    preview_fetched = pyqtSignal(int, object)

    def __init__(self):
        super().__init__()

        self._match: t.Optional[ScheduledMatch] = None

        self._participants_model = ListTableModel(ParticipantsSchema())

        self._participants_view: ReadOnlyListTableView[TournamentParticipant] = ReadOnlyListTableView()
        self.setFocusProxy(self._participants_view)
        self._participants_view.setModel(self._participants_model)
        self._participants_view.item_selected.connect(lambda p: Context.editor.open_limited_deck(p.deck.id))

        self._name_label = QtWidgets.QLabel()
        self._name_label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self._round_label = QtWidgets.QLabel()
        self._round_label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)

        self._deck_cache: t.MutableMapping[int, t.Optional[LimitedDeck]] = {}

        self._deck_preview_model = DeckModel(mode=CubeEditMode.CLOSED)
        self._deck_preview = DeckView(
            self._deck_preview_model,
            Context.get_undo_stack(),
        )

        self._no_preview_view = QtWidgets.QLabel("No preview selected")
        self._no_preview_view.setAlignment(Qt.AlignCenter)

        self._preview_unavailable_view = QtWidgets.QLabel("Preview unavailable")
        self._preview_unavailable_view.setAlignment(Qt.AlignCenter)

        self._preview_stack = QtWidgets.QStackedWidget()
        self._preview_stack.addWidget(self._deck_preview)
        self._preview_stack.addWidget(self._preview_unavailable_view)
        self._preview_stack.addWidget(self._no_preview_view)
        self._preview_stack.setCurrentWidget(self._no_preview_view)

        self.preview_fetched.connect(self._on_retrieved_deck)
        self._participants_view.current_item_changed.connect(self._on_participant_selected)

        self._open_button = QtWidgets.QPushButton("Open")
        self._open_button.clicked.connect(self._on_open_clicked)
        self._open_all_button = QtWidgets.QPushButton("Open All")
        self._open_all_button.clicked.connect(self._on_open_all_clicked)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(5, 0, 5, 0)

        top_bar.addWidget(self._name_label)
        top_bar.addStretch()
        top_bar.addWidget(self._round_label)

        splitter = QtWidgets.QSplitter(Qt.Horizontal)

        participants_view = QtWidgets.QWidget()

        participants_layout = QtWidgets.QVBoxLayout(participants_view)
        participants_layout.setContentsMargins(0, 0, 0, 0)

        participants_control_bar_layout = QtWidgets.QHBoxLayout()
        participants_control_bar_layout.setContentsMargins(0, 0, 0, 0)
        participants_control_bar_layout.addWidget(self._open_button)
        participants_control_bar_layout.addWidget(self._open_all_button)

        participants_layout.addWidget(self._participants_view)
        participants_layout.addLayout(participants_control_bar_layout)

        splitter.addWidget(participants_view)
        splitter.addWidget(self._preview_stack)

        layout.addLayout(top_bar)
        layout.addWidget(splitter)

    def _on_open_clicked(self) -> None:
        participant = self._participants_view.current()
        if participant is not None:
            Context.editor.open_limited_deck(participant.deck.id)

    def _on_open_all_clicked(self) -> None:
        for participant in self._participants_model.lines:
            Context.editor.open_limited_deck(participant.deck.id)

    def set_match(self, match: ScheduledMatch) -> None:
        if match == self._match:
            return

        self._preview_stack.setCurrentWidget(self._no_preview_view)
        self._match = match
        self._name_label.setText(match.tournament.name)
        self._round_label.setText(f"Round {match.round}")
        self._participants_model.set_lines([seat.participant for seat in match.seats])

    def clear_cache(self) -> None:
        self._deck_cache.clear()

    def _on_participant_selected(self, participant: TournamentParticipant) -> None:
        if participant.deck.id in self._deck_cache:
            self._set_preview_deck(self._deck_cache[participant.deck.id])
        else:
            Context.cube_api_client.limited_deck(participant.deck.id).then(
                lambda deck: self.preview_fetched.emit(deck.id, deck)
            ).catch(lambda e: self.preview_fetched.emit(participant.deck.id, None))

    def _set_preview_deck(self, deck: t.Optional[LimitedDeck]) -> None:
        if deck is None:
            self._preview_stack.setCurrentWidget(self._preview_unavailable_view)
            return

        self._preview_stack.setCurrentWidget(self._deck_preview)

        for scene, printings in (
            (self._deck_preview_model.maindeck, deck.deck.maindeck),
            (self._deck_preview_model.sideboard, deck.deck.sideboard),
        ):
            scene.get_cube_modification(
                remove=scene.items(),
                add=[SceneCard.from_cubeable(printing) for printing in printings],
                closed_operation=True,
            ).redo()
            scene.get_default_sort().redo()

        for cube_view in self._deck_preview.cube_views:
            cube_view.cube_image_view.fit_cards()

    def _on_retrieved_deck(self, deck_id: int, deck: t.Optional[LimitedDeck]) -> None:
        self._deck_cache[deck_id] = deck
        self._set_preview_deck(deck)


class ScheduledMatchesView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self._matches_model = ListTableModel(MatchSchema())

        self._matches_list = ReadOnlyListTableView()
        self.setFocusProxy(self._matches_list)
        self._matches_list.setModel(self._matches_model)

        self._match_view = ScheduledMatchView()

        self._matches_list.current_item_changed.connect(self._match_view.set_match)
        self._matches_list.item_selected.connect(lambda: self._match_view.setFocus())

        self._refresh_button = QtWidgets.QPushButton("Refresh")

        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        MATCHES_CONTROLLER.matches_changed.connect(self._on_matches_changed)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QtWidgets.QSplitter(Qt.Vertical)

        splitter.addWidget(self._matches_list)
        splitter.addWidget(self._match_view)

        layout.addWidget(splitter)
        layout.addWidget(self._refresh_button)

    def _on_matches_changed(self, matches: t.AbstractSet[ScheduledMatch]) -> None:
        self._refresh_button.setEnabled(True)
        self._match_view.clear_cache()
        self._matches_model.set_lines(sorted(matches, key=lambda m: m.tournament.created_at, reverse=True))

    def _on_refresh_clicked(self) -> None:
        self._refresh_button.setEnabled(False)
        MATCHES_CONTROLLER.refresh()
