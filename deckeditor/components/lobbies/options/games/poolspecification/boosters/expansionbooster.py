from __future__ import annotations

import typing as t

from mtgorp.models.persistent.attributes.expansiontype import ExpansionType
from PyQt5 import QtWidgets

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.poolspecification.interface import (
    BoosterSpecificationSelectorInterface,
)
from deckeditor.context.context import Context


class ExpansionBoosterSpecificationSelector(QtWidgets.QWidget):
    def __init__(
        self,
        lobby_view: LobbyViewInterface,
        booster_specification_selector: BoosterSpecificationSelectorInterface,
    ):
        super().__init__()

        self._booster_specification_selector = booster_specification_selector

        self._expansion_code_selector = QtWidgets.QComboBox()

        for expansion in sorted(Context.db.expansions.values(), key=lambda e: e.release_date, reverse=True):
            if expansion.expansion_type == ExpansionType.SET:
                self._expansion_code_selector.addItem(expansion.code)

        self._expansion_code_selector.activated.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                "expansion_code",
                self._expansion_code_selector.itemText(v),
            )
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._expansion_code_selector)
        layout.addStretch()

    def get_default_values(self) -> t.Mapping[str, t.Any]:
        return {
            "type": "ExpansionBoosterSpecification",
            "expansion_code": self._expansion_code_selector.itemText(0),
            "amount": 1,
        }

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._expansion_code_selector.setCurrentText(specification["expansion_code"])
        self._expansion_code_selector.setEnabled(enabled)
