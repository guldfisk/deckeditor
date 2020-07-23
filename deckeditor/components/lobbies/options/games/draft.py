from __future__ import annotations

import typing as t

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.sealed import SealedOptionsSelector
from deckeditor.components.lobbies.options.primitives import ComboSelector, CheckboxSelector


class DraftOptionsSelector(SealedOptionsSelector):

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__(lobby_view)

        self._draft_format_selector = ComboSelector(lobby_view, 'draft_format', {'single_pick', 'burn'})
        self._reverse_selector = CheckboxSelector(lobby_view, 'reverse')

        self._layout.addWidget(self._draft_format_selector, 4, 0, 1, 1)
        self._layout.addWidget(self._reverse_selector, 4, 1, 1, 1)

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        super().update_content(options, enabled)
        self._draft_format_selector.update_content(options['draft_format'], enabled)
        self._reverse_selector.update_content(options, enabled)
