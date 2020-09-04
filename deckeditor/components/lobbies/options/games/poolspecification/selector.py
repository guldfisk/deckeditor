from __future__ import annotations

import copy
import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTableWidgetItem

from mtgorp.models.serilization.strategies.raw import RawStrategy

from cubeclient.models import CubeBoosterSpecification

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.poolspecification.boosters.allcardsbooster import AllCardsBoosterSpecificationSelector
from deckeditor.components.lobbies.options.games.poolspecification.boosters.chaosbooster import ChaosBoosterSpecificationSelector
from deckeditor.components.lobbies.options.games.poolspecification.boosters.cubebooster import CubeBoosterSpecificationSelector
from deckeditor.components.lobbies.options.games.poolspecification.boosters.expansionbooster import ExpansionBoosterSpecificationSelector
from deckeditor.components.lobbies.options.games.poolspecification.interface import BoosterSpecificationSelectorInterface
from deckeditor.context.context import Context


class BoosterSpecificationSelector(QtWidgets.QStackedWidget, BoosterSpecificationSelectorInterface):
    booster_specification_value_changed = pyqtSignal(str, object)

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__()

        self._cube_booster_specification_selector = CubeBoosterSpecificationSelector(lobby_view, self)
        self._expansion_booster_specification_selector = ExpansionBoosterSpecificationSelector(lobby_view, self)
        self._all_cards_booster_selector = AllCardsBoosterSpecificationSelector(lobby_view, self)
        self._chaos_booster_selector = ChaosBoosterSpecificationSelector(lobby_view, self)

        self.specification_type_map = {
            'CubeBoosterSpecification': self._cube_booster_specification_selector,
            'ExpansionBoosterSpecification': self._expansion_booster_specification_selector,
            'AllCardsBoosterSpecification': self._all_cards_booster_selector,
            'ChaosBoosterSpecification': self._chaos_booster_selector,
        }

        for selector in self.specification_type_map.values():
            self.addWidget(selector)

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        selector = self.specification_type_map[specification['type']]
        self.setCurrentWidget(selector)
        selector.update_content(specification, enabled)


class BoosterSpecificationsTable(QtWidgets.QTableWidget):

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__(0, 2)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        self._lobby_view = lobby_view

        self._enabled = True

        self.setHorizontalHeaderLabels(
            (
                'Booster Type',
                'amount',
            )
        )
        self._specifications: t.List[t.Mapping[str, t.Any]] = []

        self.itemChanged.connect(self._handle_item_edit)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        pressed_key = key_event.key()

        if pressed_key == QtCore.Qt.Key_Delete and self._enabled:
            current_specifications = copy.copy(self._lobby_view.lobby.game_options['pool_specification'])
            for idx in sorted(self.selectedIndexes(), reverse = True):
                if len(current_specifications) > 1:
                    del current_specifications[idx.column()]
                else:
                    break

            self._lobby_view.lobby_model.set_options(
                self._lobby_view.lobby.name,
                {'pool_specification': current_specifications},
            )

    def _handle_item_edit(self, item: QtWidgets.QTableWidgetItem):
        if not item.column() == 1:
            return

        current_specifications = copy.copy(self._lobby_view.lobby.game_options['pool_specification'])
        current_specifications[item.row()]['amount'] = int(item.data(0))

        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {'pool_specification': current_specifications},
        )

    def update_content(self, specifications: t.List[t.Mapping[str, t.Any]], enabled: bool) -> None:
        self.blockSignals(True)
        self._enabled = enabled
        self.setEditTriggers(self.DoubleClicked if enabled else self.NoEditTriggers)

        self._specifications = specifications

        self.setRowCount(len(self._specifications))

        for idx, specification in enumerate(self._specifications):
            item = QTableWidgetItem(specification['type'])
            self.setItem(
                idx,
                0,
                item,
            )
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)

            self.setItem(
                idx,
                1,
                QTableWidgetItem(str(specification['amount'])),
            )

        self.resizeColumnsToContents()
        self.blockSignals(False)


class PoolSpecificationSelector(QtWidgets.QWidget):

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__()

        self._lobby_view = lobby_view

        self._specifications: t.List[t.Mapping[str, t.Any]] = []

        self._current_specification_index = 0
        self._enabled = True

        self._booster_specifications_table = BoosterSpecificationsTable(lobby_view)
        self._booster_specifications_selector = BoosterSpecificationSelector(lobby_view)

        self._add_booster_specification_button = QtWidgets.QPushButton('Add Booster')

        self._add_booster_specification_type_selector = QtWidgets.QComboBox()
        self._add_booster_specification_type_selector.addItem('CubeBoosterSpecification')
        self._add_booster_specification_type_selector.addItem('ExpansionBoosterSpecification')
        self._add_booster_specification_type_selector.addItem('AllCardsBoosterSpecification')
        self._add_booster_specification_type_selector.addItem('ChaosBoosterSpecification')

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)

        layout.addWidget(self._booster_specifications_table, 0, 0, 1, 2)
        layout.addWidget(self._add_booster_specification_type_selector, 1, 0, 1, 1)
        layout.addWidget(self._add_booster_specification_button, 1, 1, 1, 1, )
        layout.addWidget(self._booster_specifications_selector, 0, 3, 1, 1)

        self._add_booster_specification_button.clicked.connect(self._on_add_booster_specification)
        self._booster_specifications_table.currentCellChanged.connect(self._on_booster_specification_index_change)
        self._booster_specifications_selector.booster_specification_value_changed.connect(
            self._on_booster_specification_value_change
        )

    def _on_booster_specification_value_change(self, option: str, value: t.Any) -> None:
        current_options = copy.copy(self._lobby_view.lobby.game_options['pool_specification'])
        current_options[self._current_specification_index][option] = value

        if len(current_options) == 1 and current_options[0]['type'] == CubeBoosterSpecification.__name__ and option == 'release':
            Context.cube_api_client.release(value).then(
                lambda release: self._lobby_view.lobby_model.set_options(
                    self._lobby_view.lobby.name,
                    {'infinites': RawStrategy.serialize(release.infinites)},
                )
            )

        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {'pool_specification': current_options},
        )

    def _on_booster_specification_index_change(
        self,
        current_row: int,
        current_column: int,
        previous_row: int,
        previous_column: int,
    ) -> None:
        if current_row == self._current_specification_index:
            return
        self._current_specification_index = current_row
        self._booster_specifications_selector.update_content(
            self._lobby_view.lobby.game_options['pool_specification'][self._current_specification_index],
            self._enabled
        )

    def _on_add_booster_specification(self) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {
                'pool_specification': self._lobby_view.lobby.game_options['pool_specification'] + [
                    self._booster_specifications_selector.specification_type_map[
                        self._add_booster_specification_type_selector.currentText()
                    ].get_default_values()
                ],
            },
        )

    def update_content(self, specifications: t.List[t.Mapping[str, t.Any]], enabled: bool) -> None:
        self._enabled = enabled
        self._specifications = specifications
        self._booster_specifications_table.update_content(specifications, enabled)
        self._current_specification_index = min(self._current_specification_index, len(specifications) - 1)
        self._booster_specifications_selector.update_content(
            specifications[self._current_specification_index],
            enabled,
        )
        self._add_booster_specification_type_selector.setVisible(enabled)
        self._add_booster_specification_button.setVisible(enabled)
