from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.base import BaseGameOptionsSelector
from deckeditor.components.lobbies.options.primitives import ComboSelector, CheckboxSelector, IntegerOptionSelector


class DraftOptionsSelector(BaseGameOptionsSelector):

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__(lobby_view)

        self._draft_format_selector = ComboSelector(lobby_view, 'draft_format', {'single_pick', 'burn'})
        self._reverse_selector = CheckboxSelector(lobby_view, 'reverse')
        self._cheating_selector = CheckboxSelector(lobby_view, 'allow_cheating')
        self._use_time_controls_selector = CheckboxSelector(lobby_view, 'use_time_controls')
        self._time_controls_selector = IntegerOptionSelector(lobby_view, (0, 60 * 60))

        self._time_controls_selector.valueChanged.connect(
            lambda v: self._lobby_view.lobby_model.set_options(
                lobby_view.lobby.name,
                {'time_control': v},
            )
        )

        self._draft_options = QtWidgets.QHBoxLayout()
        self._draft_options.setContentsMargins(0, 0, 0, 0)

        self._draft_options.addWidget(self._draft_format_selector)
        self._draft_options.addWidget(self._reverse_selector)
        self._draft_options.addWidget(self._cheating_selector)
        self._draft_options.addWidget(self._use_time_controls_selector)
        self._draft_options.addWidget(self._time_controls_selector)

        self._layout.addLayout(self._draft_options, 5, 0, 1, 2)

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        super().update_content(options, enabled)
        self._draft_format_selector.update_content(options['draft_format'], enabled)
        self._reverse_selector.update_content(options, enabled)
        self._cheating_selector.update_content(options, enabled)
        self._use_time_controls_selector.update_content(options, enabled)
        self._time_controls_selector.update_content(options['time_control'], enabled and options['use_time_controls'])
