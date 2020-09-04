from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.poolspecification.interface import BoosterSpecificationSelectorInterface


class ChaosBoosterSpecificationSelector(QtWidgets.QWidget):

    def __init__(
        self,
        lobby_view: LobbyViewInterface,
        booster_specification_selector: BoosterSpecificationSelectorInterface,
    ):
        super().__init__()

        self._booster_specification_selector = booster_specification_selector

        self._same_selector = QtWidgets.QCheckBox('Same boosters')

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._same_selector)
        layout.addStretch()

        self._same_selector.stateChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                'same',
                v == 2,
            )
        )

    def get_default_values(self) -> t.Mapping[str, t.Any]:
        return {
            'type': 'ChaosBoosterSpecification',
            'amount': 1,
            'same': False,
        }

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._same_selector.blockSignals(True)
        self._same_selector.setChecked(specification['same'])
        self._same_selector.setEnabled(enabled)
        self._same_selector.blockSignals(False)