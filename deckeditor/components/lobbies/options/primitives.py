from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.selector import OptionsSelector


class ComboSelector(QtWidgets.QComboBox, OptionsSelector):
    def __init__(self, lobby_view: LobbyViewInterface, option: str, options: t.AbstractSet[str]):
        super().__init__()
        self._option = option

        self._lobby_view = lobby_view

        for option in sorted(options):
            self.addItem(option)

        self.activated.connect(self._on_activated)

    def update_content(self, value: str, enabled: bool) -> None:
        self.setCurrentText(value)
        self.setEnabled(enabled)

    def _on_activated(self, idx: int) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {self._option: self.itemText(idx)},
        )


class CheckboxSelector(QtWidgets.QCheckBox, OptionsSelector):
    def __init__(self, lobby_view: LobbyViewInterface, option: str):
        super().__init__(" ".join(w.capitalize() for w in option.split("_")))
        self._option = option

        self._lobby_view = lobby_view

        self.stateChanged.connect(self._on_activated)

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        self.blockSignals(True)
        self.setChecked(options[self._option])
        self.setEnabled(enabled)
        self.blockSignals(False)

    def _on_activated(self, state: int) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {self._option: state == 2},
        )


class IntegerOptionSelector(QtWidgets.QSpinBox, OptionsSelector):
    def __init__(self, lobby_view: LobbyViewInterface, allowed_range: t.Tuple[int, int] = (1, 180)):
        super().__init__()
        self._lobby_view = lobby_view
        self.setRange(*allowed_range)

    def update_content(self, value: int, enabled: bool) -> None:
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)
        self.setEnabled(enabled)
