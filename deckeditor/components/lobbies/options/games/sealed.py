from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget

from deckeditor.components.lobbies.options.infinites import InfinitesSelector
from mtgorp.models.formats.format import Format

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.poolspecification.selector import PoolSpecificationSelector
from deckeditor.components.lobbies.options.primitives import ComboSelector, CheckboxSelector
from deckeditor.components.lobbies.options.selector import OptionsSelector


class SealedOptionsSelector(QWidget, OptionsSelector):

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__()

        self._lobby_view = lobby_view

        self._format_selector = ComboSelector(lobby_view, 'format', Format.formats_map.keys())

        self._open_decks_selector = CheckboxSelector(lobby_view, 'open_decks')
        self._open_pools_selector = CheckboxSelector(lobby_view, 'open_pools')

        self._pool_specification_selector = PoolSpecificationSelector(lobby_view)

        self._infinites_selector = InfinitesSelector(lobby_view)

        self._layout = QtWidgets.QGridLayout(self)
        self._layout.setContentsMargins(0, 1, 0, 1)

        self._layout.addWidget(self._format_selector, 0, 0, 1, 2)
        self._layout.addWidget(self._pool_specification_selector, 1, 0, 1, 2)

        self._layout.addWidget(self._open_decks_selector, 2, 0, 1, 1)
        self._layout.addWidget(self._open_pools_selector, 2, 1, 1, 1)

        self._layout.addWidget(self._infinites_selector, 3, 0, 1, 2)

    def _on_open_decks_state_changed(self, state) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {'open_decks': state == 2},
        )

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._format_selector.update_content(options['format'], enabled)
        self._pool_specification_selector.update_content(options['pool_specification'], enabled)
        self._infinites_selector.update_content(options, enabled)

        self._open_decks_selector.update_content(options, enabled)
        self._open_pools_selector.update_content(options, enabled)
