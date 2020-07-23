from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.poolspecification.interface import BoosterSpecificationSelectorInterface


class AllCardsBoosterSpecificationSelector(QtWidgets.QWidget):

    def __init__(
        self,
        lobby_view: LobbyViewInterface,
        booster_specification_selector: BoosterSpecificationSelectorInterface,
    ):
        super().__init__()

        self._booster_specification_selector = booster_specification_selector

        self._respect_printings_selector = QtWidgets.QCheckBox('Respect Printings')

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._respect_printings_selector)
        layout.addStretch()

        self._respect_printings_selector.stateChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                'respect_printings',
                v == 2,
            )
        )

    def get_default_values(self) -> t.Mapping[str, t.Any]:
        return {
            'type': 'AllCardsBoosterSpecification',
            'amount': 1,
            'respect_printings': True,
        }

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._respect_printings_selector.blockSignals(True)
        self._respect_printings_selector.setChecked(specification['respect_printings'])
        self._respect_printings_selector.setEnabled(enabled)
        self._respect_printings_selector.blockSignals(False)