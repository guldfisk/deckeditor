from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.draft import DraftOptionsSelector
from deckeditor.components.lobbies.options.games.sealed import SealedOptionsSelector


class GameOptionsSelector(QtWidgets.QStackedWidget):

    def __init__(self, lobby_view: LobbyViewInterface):
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