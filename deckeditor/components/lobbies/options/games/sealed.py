from __future__ import annotations

import typing as t

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.base import BaseGameOptionsSelector
from deckeditor.components.lobbies.options.primitives import CheckboxSelector


class SealedOptionsSelector(BaseGameOptionsSelector):

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__(lobby_view)

        self._mirrored_selector = CheckboxSelector(lobby_view, 'mirrored')

        self._layout.addWidget(self._mirrored_selector, 4, 0, 1, 1)

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        super().update_content(options, enabled)
        self._mirrored_selector.update_content(options, enabled)
