from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.base import BaseGameOptionsSelector
from deckeditor.components.lobbies.options.primitives import ComboSelector, CheckboxSelector


class DraftOptionsSelector(BaseGameOptionsSelector):

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__(lobby_view)

        self._draft_format_selector = ComboSelector(lobby_view, 'draft_format', {'single_pick', 'burn'})
        self._reverse_selector = CheckboxSelector(lobby_view, 'reverse')
        self._cheating_selector = CheckboxSelector(lobby_view, 'allow_cheating')

        self._draft_options = QtWidgets.QHBoxLayout()
        self._draft_options.setContentsMargins(0, 0, 0, 0)

        self._draft_options.addWidget(self._draft_format_selector)
        self._draft_options.addWidget(self._reverse_selector)
        self._draft_options.addWidget(self._cheating_selector)

        self._layout.addLayout(self._draft_options, 5, 0, 1, 2)

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        super().update_content(options, enabled)
        self._draft_format_selector.update_content(options['draft_format'], enabled)
        self._reverse_selector.update_content(options, enabled)
        self._cheating_selector.update_content(options, enabled)
