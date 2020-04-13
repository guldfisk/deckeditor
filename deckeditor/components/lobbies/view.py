from __future__ import annotations

import copy
import itertools
import typing as t

from frozendict import frozendict
from bidict import bidict

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QMessageBox

from mtgorp.models.formats.format import Format
from mtgorp.models.persistent.attributes.expansiontype import ExpansionType

from lobbyclient.client import LobbyClient, Lobby

from deckeditor.context.context import Context


class _LobbyClient(LobbyClient):

    def __init__(self, model: LobbyModelClientConnection, url: str, token: str):
        super().__init__(url, token)
        self._model = model

    def _lobbies_changed(
        self,
        created: t.Mapping[str, Lobby] = frozendict(),
        modified: t.Mapping[str, Lobby] = frozendict(),
        closed: t.AbstractSet[str] = frozenset(),
    ) -> None:
        self._model.changed.emit()

    def _on_error(self, error):
        super()._on_error(error)
        self._model.on_disconnected()

    def _on_client_error(self, message: t.Mapping[str, t.Any]) -> None:
        message = message.get('message')
        if message is not None:
            Context.notification_message.emit(message)

    def _on_close(self):
        super()._on_close()

    def _game_started(self, lobby: Lobby, key: str) -> None:
        if lobby.game_type == 'sealed':
            Context.sealed_started.emit(int(key))
        elif lobby.game_type == 'draft':
            Context.draft_started.emit(key)


class LobbyModelClientConnection(QObject):
    changed = pyqtSignal()
    connected = pyqtSignal(bool)

    def __init__(self, parent: t.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._lobby_client: t.Optional[LobbyClient] = None

        if Context.cube_api_client.token:
            self._logged_in(None)

        Context.token_changed.connect(self._logged_in)

    @property
    def is_connected(self) -> bool:
        return self._lobby_client is not None

    def on_disconnected(self):
        self._lobby_client = None
        self.connected.emit(False)
        self.changed.emit()

    def _logged_in(self, _):
        if self._lobby_client is not None:
            self._lobby_client.close()

        self._lobby_client = _LobbyClient(
            self,
            url = 'ws://' + Context.cube_api_client.host + '/ws/lobbies/',
            token = Context.cube_api_client.token,
        )
        self.connected.emit(True)

    def get_lobbies(self) -> t.Mapping[str, Lobby]:
        if self._lobby_client is None:
            return {}
        return self._lobby_client.get_lobbies()

    def get_lobby(self, name: str) -> t.Optional[Lobby]:
        if self._lobby_client is None:
            return None
        return self._lobby_client.get_lobby(name)

    def create_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.create_lobby(name)

    def set_options(self, name: str, options: t.Any) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_options(name, options)

    def set_game_type(self, name: str, game_type: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_game_type(name, game_type)

    def leave_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.leave_lobby(name)

    def join_lobby(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.join_lobby(name)

    def set_ready(self, name: str, ready: bool) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.set_ready(name, ready)

    def start_game(self, name: str) -> None:
        if self._lobby_client is None:
            return
        self._lobby_client.start_game(name)


class LobbiesListView(QTableWidget):

    def __init__(self, parent: LobbiesView):
        super().__init__(0, 6, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'game_type', 'state', 'owner', 'users', 'size')
        )

        self._lobby_view = parent

        self._lobbies: t.List[Lobby] = []

        self._update_content()
        self._lobby_view.lobby_model.changed.connect(self._update_content)

        self.setEditTriggers(self.NoEditTriggers)

        self.cellDoubleClicked.connect(self._cell_double_clicked)

    def _cell_double_clicked(self, row: int, column: int) -> None:
        self._lobby_view.lobby_model.join_lobby(
            self._lobbies[row].name
        )

    def _update_content(self) -> None:
        def _set_data_at(data: str, _row: int, _column: int):
            _item = QTableWidgetItem()
            _item.setData(0, data)
            self.setItem(_row, _column, _item)

        self._lobbies = sorted(
            self._lobby_view.lobby_model.get_lobbies().values(),
            key = lambda l: l.name,
        )
        self.setRowCount(len(self._lobbies))

        for index, lobby in enumerate(self._lobbies):
            for column, value in enumerate(
                (
                    lobby.name,
                    lobby.game_type,
                    lobby.state,
                    lobby.owner,
                    str(len(lobby.users)),
                    str(lobby.size),
                )
            ):
                _set_data_at(value, index, column)

        self.resizeColumnsToContents()


class LobbyUserListView(QTableWidget):

    def __init__(self, lobby_model: LobbyModelClientConnection, lobby_name: str, parent: t.Optional[QObject] = None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(
            ('name', 'ready')
        )

        self._lobby_model = lobby_model
        self._lobby_name = lobby_name

        self._update_content()
        self._lobby_model.changed.connect(self._update_content)

        self.resizeColumnsToContents()

    def _update_content(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)

        users = () if lobby is None else lobby.users.values()
        self.setRowCount(len(users))

        for index, user in enumerate(sorted(users, key = lambda u: u.username)):
            item = QTableWidgetItem()
            item.setData(0, user.username)
            self.setItem(index, 0, item)

            item = QTableWidgetItem()
            item.setData(0, 'ready' if user.ready else 'unready')
            self.setItem(index, 1, item)


class ReleaseSelector(QWidget):
    release_selected = pyqtSignal(int)

    def __init__(self, lobby_view: LobbyView):
        super().__init__()
        self._lobby_view = lobby_view

        self._cube_selector = QtWidgets.QComboBox()
        self._release_selector = QtWidgets.QComboBox()

        layout = QtWidgets.QHBoxLayout()

        layout.addWidget(self._cube_selector)
        layout.addWidget(self._release_selector)

        self.setLayout(layout)

        self._versioned_cubes = list(Context.cube_api_client.versioned_cubes())
        self._release_versioned_cube_map = {
            release.id: versioned_cube
            for versioned_cube in
            self._versioned_cubes
            for release in
            versioned_cube.releases
        }

        self._update()

        self._cube_selector.activated.connect(self._on_cube_selected)
        self._release_selector.activated.connect(self._on_release_selected)

    def update_content(self, release_id: t.Union[str, int], enabled: bool) -> None:
        versioned_cube = self._release_versioned_cube_map[release_id]
        self._cube_selector.setCurrentIndex(
            self._versioned_cubes.index(
                self._release_versioned_cube_map[release_id]
            )
        )
        idx = 0
        self._release_selector.clear()
        for _idx, release in enumerate(versioned_cube.releases):
            self._release_selector.addItem(release.name, release.id)
            if release.id == release_id:
                idx = _idx

        self._release_selector.setCurrentIndex(idx)

        self._cube_selector.setEnabled(enabled)
        self._release_selector.setEnabled(enabled)

    def _update(self):
        self._cube_selector.clear()
        for versioned_cube in self._versioned_cubes:
            self._cube_selector.addItem(versioned_cube.name, versioned_cube.id)

    def _on_release_selected(self, idx: int) -> None:
        self.release_selected.emit(self._release_selector.itemData(idx))

    def _on_cube_selected(self, idx: int) -> None:
        versioned_cube = self._versioned_cubes[idx]
        if not self._release_selector.currentData() in (
            release.id
            for release in
            versioned_cube.releases
        ):
            self._release_selector.clear()
            for release in versioned_cube.releases:
                self._release_selector.addItem(release.name, release.id)

            self._release_selector.setCurrentIndex(0)

            self.release_selected.emit(self._release_selector.itemData(0))


class BoosterSpecificationsTable(QtWidgets.QTableWidget):

    def __init__(self, lobby_view: LobbyView):
        super().__init__(0, 2)

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
            current_specifications = copy.copy(self._lobby_view.lobby.options['pool_specification'])
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

        current_specifications = copy.copy(self._lobby_view.lobby.options['pool_specification'])
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


class CubeBoosterSpecificationSelector(QtWidgets.QWidget):

    def __init__(self, lobby_view: LobbyView, booster_specification_selector: BoosterSpecificationSelector):
        super().__init__()

        self._booster_specification_selector = booster_specification_selector

        self._release_selector = ReleaseSelector(lobby_view)
        self._size_selector = IntegerOptionSelector(lobby_view, allowed_range = (1, 360))
        self._allow_intersection_label = QtWidgets.QLabel('Allow Intersections')
        self._allow_intersection_selector = QtWidgets.QCheckBox()
        self._allow_repeat_label = QtWidgets.QLabel('Allow Repeats')
        self._allow_repeat_selector = QtWidgets.QCheckBox()

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._release_selector)
        layout.addWidget(self._size_selector)

        flags_layout = QtWidgets.QHBoxLayout()

        flags_layout.addWidget(self._allow_intersection_label)
        flags_layout.addWidget(self._allow_intersection_selector)
        flags_layout.addWidget(self._allow_repeat_label)
        flags_layout.addWidget(self._allow_repeat_selector)

        layout.addLayout(flags_layout)

        self._size_selector.valueChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit('size', v)
        )
        self._release_selector.release_selected.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit('release', v)
        )
        self._allow_intersection_selector.stateChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                'allow_intersection',
                v == 2,
            )
        )
        self._allow_repeat_selector.stateChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                'allow_repeat',
                v == 2,
            )
        )

    def get_default_values(self) -> t.Mapping[str, t.Any]:
        return {
            'type': 'CubeBoosterSpecification',
            'release': sorted(
                itertools.chain(
                    *(
                        versioned_cube.releases
                        for versioned_cube in
                        Context.cube_api_client.versioned_cubes()
                    )
                ),
                key = lambda release: release.created_at,
            )[-1].id,
            'size': 90,
            'allow_intersection': False,
            'allow_repeat': False,
            'amount': 1,
        }

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._release_selector.update_content(specification['release'], enabled)
        self._size_selector.update_content(specification['size'], enabled)

        self._allow_intersection_selector.blockSignals(True)
        self._allow_intersection_selector.setEnabled(enabled)
        self._allow_intersection_selector.setChecked(specification['allow_intersection'])
        self._allow_intersection_selector.blockSignals(False)

        self._allow_repeat_selector.blockSignals(True)
        self._allow_repeat_selector.setEnabled(enabled)
        self._allow_repeat_selector.setChecked(specification['allow_repeat'])
        self._allow_repeat_selector.blockSignals(False)


class ExpansionBoosterSpecificationSelector(QtWidgets.QWidget):

    def __init__(self, lobby_view: LobbyView, booster_specification_selector: BoosterSpecificationSelector):
        super().__init__()

        self._booster_specification_selector = booster_specification_selector

        self._expansion_code_selector = QtWidgets.QComboBox()

        for expansion in sorted(Context.db.expansions.values(), key = lambda e: e.release_date, reverse = True):
            if expansion.expansion_type == ExpansionType.SET:
                self._expansion_code_selector.addItem(expansion.code)

        self._expansion_code_selector.activated.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                'expansion_code',
                self._expansion_code_selector.itemText(v),
            )
        )

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._expansion_code_selector)

    def get_default_values(self) -> t.Mapping[str, t.Any]:
        return {
            'type': 'ExpansionBoosterSpecification',
            'expansion_code': self._expansion_code_selector.itemText(0),
            'amount': 1,
        }

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._expansion_code_selector.setCurrentText(specification['expansion_code'])
        self._expansion_code_selector.setEnabled(enabled)


class AllCardsBoosterSpecificationSelector(QtWidgets.QWidget):

    def __init__(self, lobby_view: LobbyView, booster_specification_selector: BoosterSpecificationSelector):
        super().__init__()

        self._booster_specification_selector = booster_specification_selector

        self._respect_printings_selector = QtWidgets.QCheckBox()
        self._respect_printings_label = QtWidgets.QLabel('Respect Printings')

        layout = QtWidgets.QHBoxLayout(self)

        layout.addWidget(self._respect_printings_label)
        layout.addWidget(self._respect_printings_selector)

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


class BoosterSpecificationSelector(QtWidgets.QStackedWidget):
    booster_specification_value_changed = pyqtSignal(str, object)

    def __init__(self, lobby_view: LobbyView):
        super().__init__()

        self._cube_booster_specification_selector = CubeBoosterSpecificationSelector(lobby_view, self)
        self._expansion_booster_specification_selector = ExpansionBoosterSpecificationSelector(lobby_view, self)
        self._all_cards_booster_selector = AllCardsBoosterSpecificationSelector(lobby_view, self)

        self.specification_type_map = {
            'CubeBoosterSpecification': self._cube_booster_specification_selector,
            'ExpansionBoosterSpecification': self._expansion_booster_specification_selector,
            'AllCardsBoosterSpecification': self._all_cards_booster_selector,
        }

        for selector in self.specification_type_map.values():
            self.addWidget(selector)

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        selector = self.specification_type_map[specification['type']]
        self.setCurrentWidget(selector)
        selector.update_content(specification, enabled)


class PoolSpecificationSelector(QtWidgets.QWidget):

    def __init__(self, lobby_view: LobbyView):
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

        layout = QtWidgets.QHBoxLayout(self)

        add_booster_layout = QtWidgets.QHBoxLayout()

        add_booster_layout.addWidget(self._add_booster_specification_type_selector)
        add_booster_layout.addWidget(self._add_booster_specification_button)

        right_side_layout = QtWidgets.QVBoxLayout()

        right_side_layout.addWidget(self._booster_specifications_table)
        right_side_layout.addLayout(add_booster_layout)

        layout.addLayout(right_side_layout)
        layout.addWidget(self._booster_specifications_selector)

        self._add_booster_specification_button.clicked.connect(self._on_add_booster_specification)
        self._booster_specifications_table.currentCellChanged.connect(self._on_booster_specification_index_change)
        self._booster_specifications_selector.booster_specification_value_changed.connect(
            self._on_booster_specification_value_change
        )

    def _on_booster_specification_value_change(self, option: str, value: t.Any) -> None:
        current_options = copy.copy(self._lobby_view.lobby.options['pool_specification'])
        current_options[self._current_specification_index][option] = value
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
            self._lobby_view.lobby.options['pool_specification'][self._current_specification_index],
            self._enabled
        )

    def _on_add_booster_specification(self) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {
                'pool_specification': self._lobby_view.lobby.options['pool_specification'] + [
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


class ComboSelector(QtWidgets.QComboBox):

    def __init__(self, lobby_view: LobbyView, option: str, options: t.AbstractSet[str]):
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


class CheckboxSelector(QtWidgets.QCheckBox):

    def __init__(self, lobby_view: LobbyView, option: str):
        super().__init__()
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


class IntegerOptionSelector(QtWidgets.QSpinBox):

    def __init__(self, lobby_view: LobbyView, allowed_range: t.Tuple[int, int] = (1, 180)):
        super().__init__()
        self._lobby_view = lobby_view
        self.setRange(*allowed_range)

    def update_content(self, value: int, enabled: bool) -> None:
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)
        self.setEnabled(enabled)


class OptionsSelector(QWidget):

    def __init__(self, lobby_view: LobbyView):
        super().__init__()
        self._lobby_view = lobby_view

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        pass


class SealedOptionsSelector(OptionsSelector):

    def __init__(self, lobby_view: LobbyView):
        super().__init__(lobby_view)

        self._format_selector = ComboSelector(lobby_view, 'format', Format.formats_map.keys())

        self._open_decks_selector = CheckboxSelector(lobby_view, 'open_decks')
        self._open_pools_selector = CheckboxSelector(lobby_view, 'open_pools')

        self._pool_specification_selector = PoolSpecificationSelector(lobby_view)

        self._layout = QtWidgets.QVBoxLayout(self)

        self._layout.addWidget(self._format_selector, QtCore.Qt.AlignTop)
        self._layout.addWidget(self._pool_specification_selector, QtCore.Qt.AlignTop)

        information_layout = QtWidgets.QFormLayout()

        information_layout.addRow('open decks', self._open_decks_selector)
        information_layout.addRow('open pools', self._open_pools_selector)

        self._layout.addLayout(information_layout)

    def _on_open_decks_state_changed(self, state) -> None:
        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {'open_decks': state == 2},
        )

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._format_selector.update_content(options['format'], enabled)
        self._pool_specification_selector.update_content(options['pool_specification'], enabled)

        self._open_decks_selector.update_content(options, enabled)
        self._open_pools_selector.update_content(options, enabled)


class DraftOptionsSelector(SealedOptionsSelector):

    def __init__(self, lobby_view: LobbyView):
        super().__init__(lobby_view)

        self._draft_format_selector = ComboSelector(lobby_view, 'draft_format', {'single_pick', 'burn'})

        self._layout.insertWidget(0, self._draft_format_selector)

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        super().update_content(options, enabled)
        self._draft_format_selector.update_content(options['draft_format'], enabled)


class GameOptionsSelector(QtWidgets.QStackedWidget):

    def __init__(self, lobby_view: LobbyView):
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


class LobbyView(QWidget):
    options_changed = pyqtSignal(dict)

    def __init__(self, lobby_model: LobbyModelClientConnection, lobby_name: str, parent: t.Optional[QObject] = None):
        super().__init__(parent)
        self._lobby_model = lobby_model
        self._lobby_name = lobby_name

        layout = QtWidgets.QVBoxLayout()

        self._ready_button = QtWidgets.QPushButton('ready')
        self._ready_button.clicked.connect(self._toggle_ready)

        self._start_game_button = QtWidgets.QPushButton('start')
        self._start_game_button.clicked.connect(self._start_game)

        self._game_type_selector = QtWidgets.QComboBox()
        self._game_type_selector.addItem('draft')
        self._game_type_selector.addItem('sealed')
        self._game_type_selector.activated.connect(self._on_game_type_selected)

        self._options_selector = GameOptionsSelector(self)
        self._options_selector_area = QtWidgets.QScrollArea()
        self._options_selector_area.setWidget(self._options_selector)

        self._reconnect_button = QtWidgets.QPushButton('reconnect')
        self._reconnect_button.clicked.connect(self._reconnect)

        users_list = LobbyUserListView(self._lobby_model, self._lobby_name)

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(self._ready_button)
        top_layout.addWidget(self._start_game_button)
        top_layout.addWidget(self._reconnect_button)

        layout.addLayout(top_layout)
        layout.addWidget(self._game_type_selector)
        layout.addWidget(self._options_selector_area)
        layout.addWidget(users_list)

        self._update_content()
        self._lobby_model.changed.connect(self._update_content)

        self.setLayout(layout)

    @property
    def lobby(self) -> t.Optional[Lobby]:
        return self._lobby_model.get_lobby(self._lobby_name)

    @property
    def lobby_model(self) -> LobbyModelClientConnection:
        return self._lobby_model

    def _on_game_type_selected(self, idx: int) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if lobby is None:
            return

        user = lobby.users.get(Context.cube_api_client.user.username)
        if user and user.username == lobby.owner:
            self._lobby_model.set_game_type(self._lobby_name, self._game_type_selector.itemText(idx))

    def _toggle_ready(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if lobby:
            user = lobby.users.get(Context.cube_api_client.user.username)
            if user is not None:
                self._lobby_model.set_ready(
                    self._lobby_name,
                    not user.ready,
                )

    def _start_game(self) -> None:
        self._lobby_model.start_game(self._lobby_name)

    def _reconnect(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if lobby.game_type == 'draft':
            Context.draft_started.emit(lobby.key)

    def _update_content(self) -> None:
        lobby = self._lobby_model.get_lobby(self._lobby_name)
        if not lobby:
            return

        user = lobby.users.get(Context.cube_api_client.user.username)
        if user is None:
            return

        can_edit_options = Context.cube_api_client.user.username == lobby.owner and lobby.state == 'pre-game'

        self._ready_button.setText(
            'unready' if user.ready else 'ready'
        )
        self._ready_button.setVisible(lobby.state == 'pre-game')

        self._reconnect_button.setVisible(lobby.state == 'game')

        self._game_type_selector.setEnabled(can_edit_options)

        self._game_type_selector.setCurrentText(lobby.game_type)
        self._options_selector.update_content(lobby.game_type, lobby.options, can_edit_options)

        self._start_game_button.setVisible(
            lobby.state == 'pre-game'
            and Context.cube_api_client.user.username == lobby.owner
            and all(
                user.ready
                for user in
                lobby.users.values()
            )
        )


class CreateLobbyDialog(QtWidgets.QDialog):

    def __init__(self, parent: LobbiesView = None):
        super().__init__(parent)
        self._lobby_view = parent

        self._ok_button = QtWidgets.QPushButton('Ok', self)
        self._lobby_name_selector = QtWidgets.QLineEdit()

        self._top_box = QtWidgets.QHBoxLayout()
        self._bottom_box = QtWidgets.QHBoxLayout()

        self._top_box.addWidget(self._lobby_name_selector)

        self._bottom_box.addWidget(self._ok_button)

        self._layout = QtWidgets.QVBoxLayout()

        self._layout.addLayout(self._top_box)
        self._layout.addLayout(self._bottom_box)

        self.setLayout(self._layout)

        self._ok_button.clicked.connect(self._create)

        self._lobby_name_selector.setFocus()

    def _create(self) -> None:
        self._lobby_view.lobby_model.create_lobby(
            self._lobby_name_selector.text()
        )
        self.accept()


class LobbyTabs(QtWidgets.QTabWidget):

    def __init__(self, parent: LobbiesView):
        super().__init__(parent)
        self._lobby_view: LobbiesView = parent

        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self._tab_close_requested)
        self._lobby_view.lobby_model.changed.connect(self._update_content)

        self._tabs_map: bidict[str, int] = bidict()

    def _update_content(self) -> None:
        lobbies = {
            name: lobby
            for name, lobby in
            self._lobby_view.lobby_model.get_lobbies().items()
            if Context.cube_api_client.user.username in lobby.users
        }

        removed = self._tabs_map.keys() - lobbies.keys()
        if removed:
            for removed_name, removed_index in sorted(
                (
                    (name, self._tabs_map[name])
                    for name in
                    removed
                ),
                key = lambda kv: kv[1],
                reverse = True,
            ):
                del self._tabs_map[removed_name]

                for name, index in self._tabs_map.items():
                    if index > removed_index:
                        self._tabs_map[name] -= 1

                self.removeTab(removed_index)

        added = lobbies.keys() - self._tabs_map.keys()
        if added:
            max_index = max(self._tabs_map.values()) if self._tabs_map else -1
            for added_name in added:
                max_index += 1
                self._tabs_map[added_name] = max_index
                self.insertTab(
                    max_index,
                    LobbyView(self._lobby_view.lobby_model, added_name),
                    added_name,
                )

    def _tab_close_requested(self, index: int) -> None:
        closed_tab: LobbyView = self.widget(index)

        if closed_tab.lobby.state == 'game':
            confirm_dialog = QMessageBox()
            confirm_dialog.setText('Confirm close')
            confirm_dialog.setInformativeText(
                'You sure you want to disconnect from this ongoing game?\nYou cannot reconnect after leaving.'
            )
            confirm_dialog.setStandardButtons(QMessageBox.Close | QMessageBox.Cancel)
            confirm_dialog.setDefaultButton(QMessageBox.Cancel)
            return_code = confirm_dialog.exec_()

            if return_code == QMessageBox.Cancel:
                return

        self._lobby_view.lobby_model.leave_lobby(
            self._tabs_map.inverse[index]
        )


class LobbiesView(QWidget):
    lobbies_changed = pyqtSignal()

    def __init__(self, lobby_model: LobbyModelClientConnection, parent: t.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._lobby_model = lobby_model

        lobbies_list_view = LobbiesListView(self)

        self._lobby_tabs = LobbyTabs(self)

        layout = QtWidgets.QVBoxLayout()

        self._create_lobby_button = QtWidgets.QPushButton('Create lobby')
        self._create_lobby_button.clicked.connect(self._create_lobby)
        if not self._lobby_model.is_connected:
            self._create_lobby_button.setEnabled(False)
        self._lobby_model.connected.connect(self._on_connection_status_change)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        splitter.addWidget(lobbies_list_view)
        splitter.addWidget(self._lobby_tabs)

        layout.addWidget(splitter)
        layout.addWidget(self._create_lobby_button)

        self.setLayout(layout)

    def _on_connection_status_change(self, connected: bool) -> None:
        self._create_lobby_button.setEnabled(connected)

    @property
    def lobby_model(self) -> LobbyModelClientConnection:
        return self._lobby_model

    def set_model(self, lobby_model: LobbyModelClientConnection) -> None:
        self._lobby_model = lobby_model
        self.lobbies_changed.connect(lobby_model.changed)

    def _create_lobby(self) -> None:
        dialog = CreateLobbyDialog(self)
        dialog.exec()
