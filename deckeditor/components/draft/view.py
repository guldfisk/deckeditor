from __future__ import annotations

import threading
import typing as t
from collections import defaultdict
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor

import plyer

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QMouseEvent
from PyQt5.QtWidgets import QUndoStack, QGraphicsItem, QAbstractItemView, QMessageBox

from yeetlong.multiset import Multiset

from mtgorp.models.interfaces import Printing
from mtgorp.db.database import CardDatabase

from magiccube.collections.cubeable import Cubeable

from cubeclient.models import ApiClient, CubeBoosterSpecification

from mtgdraft.client import DraftClient
from mtgdraft.models import DraftRound, SinglePickPick, BurnPick, PickPoint, DraftConfiguration, DraftBooster, SinglePick, Burn

from deckeditor import values
from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.grid import GridAligner
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.deck import PoolModel
from deckeditor.components.views.cubeedit.cubelistview import CubeableTableItem
from deckeditor.components.editables.editor import EditablesMeta
from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from deckeditor.components.views.cubeedit.graphical.cubeimageview import CubeImageView
from deckeditor.components.draft.draftbots import collect_bots, bot_pick
from deckeditor.components.cardview.focuscard import CubeableFocusEvent
from deckeditor.components.draft.values import GHOST_COLOR, BURN_COLOR, PICK_COLOR


class _DraftClient(DraftClient):

    def __init__(self, api_client: ApiClient, draft_id: str, db: CardDatabase, draft_model: DraftModel):
        super().__init__(api_client, draft_id, db)
        self._draft_model = draft_model

    def _received_booster(self, pick_point: PickPoint) -> None:
        self._draft_model._on_received_booster(pick_point)

    def _picked(self, pick_point: PickPoint) -> None:
        self._draft_model._on_pick(pick_point)

    def _completed(self, pool_id: int, session_name: str) -> None:
        self._draft_model.draft_completed.emit(pool_id, session_name)

    def _on_start(self, draft_configuration: DraftConfiguration) -> None:
        self._draft_model.draft_started.emit(draft_configuration)

    def _on_round(self, draft_round: DraftRound) -> None:
        self._draft_model.round_started.emit(draft_round)


class DraftModel(QObject):
    connected = pyqtSignal(bool)
    received_booster = pyqtSignal(PickPoint)
    new_head = pyqtSignal(object, bool)
    picked = pyqtSignal(PickPoint, tuple, bool)
    draft_started = pyqtSignal(DraftConfiguration)
    round_started = pyqtSignal(DraftRound)
    draft_completed = pyqtSignal(int, str)

    def __init__(self, key: str) -> None:
        super().__init__()

        self._key = key
        self._draft_client: t.Optional[DraftClient] = None

        self._pending_picked_scene: t.Optional[CubeScene] = None
        self._pending_picked_position: t.Optional[QtCore.QPoint] = None

        self._pick_number_lock = threading.Lock()
        self._pick_number = 0

        self._pick_counter_head = 1

        self._pick: t.Optional[PhysicalCard] = None
        self._burn: t.Optional[PhysicalCard] = None

    @property
    def pick_point_head(self) -> t.Optional[PickPoint]:
        try:
            return self._draft_client.history[self._pick_counter_head - 1]
        except IndexError:
            return None

    def _update_head(self, head: int, new: bool = True) -> None:
        self._pick_counter_head = head
        self.new_head.emit(self.pick_point_head, new)

    def go_to_latest(self) -> None:
        latest = self._draft_client.history.current
        target_head = latest.global_pick_number + 1 if latest.pick else latest.global_pick_number
        if self._pick_counter_head >= target_head:
            return
        self._update_head(target_head)

    def go_forward(self) -> None:
        latest = self._draft_client.history.current
        if self._pick_counter_head >= (latest.global_pick_number + 1 if latest.pick else latest.global_pick_number):
            return
        self._update_head(self._pick_counter_head + 1)

    def go_to_start(self) -> None:
        if self._pick_counter_head <= 1:
            return
        self._update_head(1)

    def go_backwards(self) -> None:
        if self._pick_counter_head <= 1:
            return
        self._update_head(self._pick_counter_head - 1)

    def _on_received_booster(self, pick_point: PickPoint) -> None:
        self.received_booster.emit(pick_point)
        if self._pick_counter_head >= pick_point.global_pick_number:
            self._update_head(pick_point.global_pick_number, pick_point.global_pick_number > self._pick_number)

        if not Context.main_window.isActiveWindow() and Context.settings.value('notify_on_booster_arrived', True, bool):
            try:
                plyer.notification.notify(
                    title = 'New pack',
                    message = f'pack {pick_point.round.pack} pick {pick_point.pick_number}',
                )
            except NotImplementedError:
                Context.notification_message.emit('OS notifications not available')
                Context.settings.setValue('notify_on_booster_arrived', False)

    def _on_pick(self, pick_point: PickPoint) -> None:
        new = True
        with self._pick_number_lock:
            if pick_point.global_pick_number <= self._pick_number:
                new = False
            else:
                self._pick_number = pick_point.global_pick_number

        self.picked.emit(
            pick_point,
            (self._pending_picked_scene, self._pending_picked_position),
            new,
        )
        self._pending_picked_scene = None
        self._pending_picked_position = None
        if self._pick_counter_head >= pick_point.global_pick_number:
            self._update_head(pick_point.global_pick_number + 1, new = new)

    def connect(self) -> None:
        self._draft_client = _DraftClient(
            api_client = Context.cube_api_client,
            draft_id = self._key,
            db = Context.db,
            draft_model = self,
        )

    def close(self) -> None:
        if self._draft_client:
            self._draft_client.close()

    @property
    def draft_client(self) -> t.Optional[DraftClient]:
        return self._draft_client

    @property
    def key(self) -> str:
        return self._key

    def pick(
        self,
        card: PhysicalCard,
        scene: t.Optional[CubeScene] = None,
        position: t.Optional[QtCore.QPoint] = None,
        burn: bool = False,
        infer: bool = True,
        toggle: bool = False,
    ) -> None:
        if self._pick_counter_head != self._draft_client.history.current.global_pick_number:
            Context.notification_message.emit('Can\'t pick from historic pack')
            return

        if card.values.get('ghost'):
            return

        if not Context.settings.value('infer_pick_burn', True, bool):
            infer = False

        if isinstance(self._draft_client.draft_format, SinglePick):
            self._pending_picked_scene = scene
            self._pending_picked_position = position
            self._draft_client.draft_format.pick(SinglePickPick(card.cubeable))

        elif isinstance(self._draft_client.draft_format, Burn):
            if infer:
                if burn:
                    if self._burn is None:
                        _burn = True
                    elif self._pick is None:
                        _burn = False
                    else:
                        _burn = True
                else:
                    if self._pick is None:
                        _burn = False
                    elif self._burn is None:
                        _burn = True
                    else:
                        _burn = False
            else:
                _burn = burn

            if toggle and infer:
                if self._burn == card:
                    self._burn.clear_highlight()
                    self._burn = None
                    return
                if self._pick == card:
                    self._pick.clear_highlight()
                    self._pick = None
                    return

            if _burn:
                if self._burn:
                    self._burn.clear_highlight()
                    if toggle and card == self._burn:
                        self._burn = None
                        return
                if self._pick == card:
                    self._pick.clear_highlight()
                    self._pick = None
                self._burn = card
                self._burn.add_highlight(BURN_COLOR)
            else:
                if self._pick:
                    self._pick.clear_highlight()
                    if toggle and card == self._pick:
                        self._pick = None
                        self._pending_picked_scene = None
                        self._pending_picked_position = None
                        return
                if self._burn == card:
                    self._burn.clear_highlight()
                    self._burn = None
                self._pick = card
                self._pick.add_highlight(PICK_COLOR)
                self._pending_picked_position = position
                self._pending_picked_scene = scene

            if (
                self._pick and
                (
                    self._burn
                    or len(self._draft_client.history.current.booster.cubeables) == 1
                )
            ):
                self._pick.clear_highlight()
                if self._burn:
                    self._burn.clear_highlight()
                self._draft_client.draft_format.pick(
                    BurnPick(
                        self._pick.cubeable,
                        self._burn.cubeable if self._burn is not None else None,
                    )
                )
                self._pick = None
                self._burn = None

    def persist(self) -> t.Any:
        return {
            'pick_number': self._pick_number,
            'key': self._key,
        }

    @classmethod
    def load(cls, state: t.Any) -> DraftModel:
        draft_model = cls(key = state['key'])
        draft_model._pick_number = state['pick_number']
        print('loading draft model', draft_model._pick_number)
        return draft_model


class BoosterImageView(CubeImageView):

    def __init__(self, undo_stack: QUndoStack, scene: CubeScene, draft_model: DraftModel):
        super().__init__(undo_stack, scene)
        self._draft_model = draft_model

    def successful_drop(self, drop_event: QtGui.QDropEvent, image_view: CubeImageView) -> bool:
        if not len(self.floating) == 1:
            self.floating[:] = []
            return False

        self._draft_model.pick(
            self.floating[0],
            image_view.scene(),
            image_view.mapToScene(drop_event.pos()),
            burn = False,
            infer = False,
            toggle = False,
        )

        self.floating[:] = []
        return False

    def _context_menu_event(self, position: QtCore.QPoint):
        menu = QtWidgets.QMenu(self)

        item: QGraphicsItem = self.itemAt(position)

        if item and isinstance(item, PhysicalCard) and not item.values.get('ghost'):
            menu.addSeparator()

            pick_action = QtWidgets.QAction('Pick', menu)
            pick_action.triggered.connect(
                lambda: self._draft_model.pick(item, burn = False, infer = False, toggle = False)
            )
            menu.addAction(pick_action)

            if isinstance(self._draft_model.draft_client.draft_format, Burn):
                burn_action = QtWidgets.QAction('Burn', menu)
                burn_action.triggered.connect(
                    lambda: self._draft_model.pick(item, burn = True, infer = False, toggle = False)
                )
                menu.addAction(burn_action)

        menu.addSeparator()

        menu.addAction(self._fit_action)

        menu.addSeparator()

        menu.addAction(self._sort_action)

        sort_menu = menu.addMenu('Sorts')

        for (_, orientation), action in self._sort_actions.items():
            if orientation == QtCore.Qt.Horizontal or self._scene.aligner.supports_sort_orientation:
                sort_menu.addAction(action)

        menu.addSeparator()

        menu.addAction(self._resize_action)

        menu.exec_(self.mapToGlobal(position))


class PickMetaInfo(QtWidgets.QWidget):

    def __init__(self, draft_model: DraftModel):
        super().__init__()
        self._draft_model = draft_model

        self.setContentsMargins(0, 0, 0, 0)

        self._players_list = QtWidgets.QLabel()
        self._pack_counter_label = QtWidgets.QLabel()

        layout = QtWidgets.QHBoxLayout(self)

        layout.addWidget(self._players_list)
        layout.addWidget(self._pack_counter_label)
        layout.addStretch()

    def set_pick_point(self, pick_point: PickPoint) -> None:
        self._players_list.setText(
            'Draft order: ' + (
                ' -> '
                if pick_point.round.clockwise else
                ' <- '
            ).join(
                drafter.username
                for drafter in
                self._draft_model.draft_client.draft_configuration.drafters.all
            )
        )
        self._pack_counter_label.setText(
            'Pack: {}/{} Pick {}, {}'.format(
                pick_point.round.pack,
                sum(
                    spec.amount
                    for spec in
                    self._draft_model.draft_client.draft_configuration.pool_specification.booster_specifications
                ),
                pick_point.pick_number,
                pick_point.global_pick_number,
            )
        )


class BoosterWidget(QtWidgets.QWidget):

    def __init__(self, draft_model: DraftModel):
        super().__init__()
        self._undo_stack = Context.get_undo_stack()

        self._draft_model = draft_model

        self._latest_meta_info = PickMetaInfo(draft_model)
        self._head_meta_info = PickMetaInfo(draft_model)
        self._head_meta_info.setVisible(False)

        self._picking_info = QtWidgets.QLabel('')

        self._booster_scene = CubeScene(
            GridAligner,
            mode = CubeEditMode.CLOSED,
            width = values.IMAGE_WIDTH * 14,
            name = 'booster',
        )
        self._booster_view = CubeView(
            scene = self._booster_scene,
            undo_stack = self._undo_stack,
            cube_image_view = BoosterImageView(
                self._undo_stack,
                self._booster_scene,
                self._draft_model,
            ),
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        info_bar_layout = QtWidgets.QHBoxLayout()
        info_bar_layout.setContentsMargins(0, 0, 0, 0)

        info_bar_layout.addWidget(self._latest_meta_info)
        info_bar_layout.addWidget(self._head_meta_info)
        info_bar_layout.addStretch()
        info_bar_layout.addWidget(self._picking_info)

        layout.addLayout(info_bar_layout)
        layout.addWidget(self._booster_view)

        self._draft_model.new_head.connect(self._set_pick_point)
        self._draft_model.picked.connect(self._on_picked)
        self._draft_model.received_booster.connect(self._on_receive_booster)
        self._booster_view.cube_image_view.card_double_clicked.connect(self._on_card_double_clicked)

    @property
    def booster_scene(self) -> CubeScene:
        return self._booster_scene

    def _on_receive_booster(self, pick_point: PickPoint) -> None:
        self._update_pick_meta()

    def _on_card_double_clicked(self, card: PhysicalCard, modifiers: Qt.KeyboardModifiers):
        if not Context.settings.value('pick_on_double_click', True, bool):
            return

        self._draft_model.pick(
            card = card,
            burn = modifiers == Qt.ShiftModifier,
            infer = True,
            toggle = True,
        )

    def _update_pick_meta(self) -> None:
        pick_point = self._draft_model.pick_point_head
        latest = self._draft_model.draft_client.history.current

        self._latest_meta_info.set_pick_point(latest)

        if pick_point and pick_point != latest:
            self._head_meta_info.set_pick_point(pick_point)
            self._head_meta_info.setVisible(True)
        else:
            self._head_meta_info.setVisible(False)

        self._picking_info.setText('' if latest.pick else 'picking')

    def _clear(self) -> None:
        items = self._booster_scene.items()
        if items:
            self._booster_scene.get_cube_modification(
                remove = items,
                closed_operation = True,
            ).redo()

    def _highlight_picks_burns(
        self,
        cards: t.List[PhysicalCard],
        picked: Multiset[Cubeable],
        burned: Multiset[Cubeable]
    ):
        cubeables_to_cards_map: t.MutableMapping[Cubeable, PhysicalCard] = defaultdict(list)

        for card in cards:
            cubeables_to_cards_map[card.cubeable].append(card)

        for cubeables, color in (
            (picked, PICK_COLOR),
            (burned, BURN_COLOR),
        ):
            for cubeable, multiplicity in cubeables.items():
                for card in cubeables_to_cards_map[cubeable][:multiplicity]:
                    card.add_highlight(color)
                del cubeables_to_cards_map[cubeable][:multiplicity]

    def _set_pick_point(self, pick_point: t.Optional[PickPoint], new: bool) -> None:
        if not new:
            return

        self._update_pick_meta()
        self._booster_view.cube_image_view.cancel_drags()

        if pick_point is None:
            self._clear()
            return

        release_id = (
            pick_point.round.booster_specification.release.id
            if isinstance(pick_point.round.booster_specification, CubeBoosterSpecification) else
            []
        )

        previous_picks = (
            self._draft_model.draft_client.history.preceding_picks(pick_point)
            if Context.settings.value('ghost_cards', True, bool) else
            None
        )

        ghost_cards: t.List[PhysicalCard] = [
            PhysicalCard.from_cubeable(cubeable, release_id = release_id)
            for cubeable in
            previous_picks[0].booster.cubeables - pick_point.booster.cubeables
        ] if previous_picks else []

        cards = [
                    PhysicalCard.from_cubeable(cubeable, release_id = release_id)
                    for cubeable in
                    pick_point.booster.cubeables
                ] + ghost_cards

        self._booster_scene.get_cube_modification(
            add = cards,
            remove = self._booster_scene.items(),
            closed_operation = True,
        ).redo()

        for ghost_card in ghost_cards:
            ghost_card.add_highlight(GHOST_COLOR)
            ghost_card.values['ghost'] = True

        picks = Multiset()
        burns = Multiset()

        for _pick_point in previous_picks + ([pick_point] if pick_point.pick else []):
            if isinstance(_pick_point.pick, BurnPick):
                picks.add(_pick_point.pick.pick)
                if _pick_point.pick.burn is not None:
                    burns.add(_pick_point.pick.burn)
            else:
                picks.add(_pick_point.pick.cubeable)

        self._highlight_picks_burns(cards, picks, burns)

    def _on_picked(
        self,
        pick: PickPoint,
        target: t.Tuple[t.Optional[CubeScene], t.Optional[QtCore.QPoint]],
        new: bool,
    ) -> None:
        self._update_pick_meta()


class PicksTable(QtWidgets.QTableWidget):

    def __init__(self, draft_model: DraftModel):
        super().__init__(0, 5)

        self._draft_model = draft_model

        self.setHorizontalHeaderLabels(
            (
                'Pack',
                'Pick Number',
                'Pick',
                'Burn',
                'Booster',
            )
        )

        self.setMouseTracking(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._current_pack = 0

        self.currentCellChanged.connect(self._handle_current_cell_changed)

        self._draft_model.round_started.connect(self._on_round_started)
        self._draft_model.picked.connect(self._on_picked)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        item = self.itemAt(event.pos())
        if item is not None:
            Context.focus_card_changed.emit(CubeableFocusEvent(self.item(item.row(), 2).cubeable))

    def _handle_current_cell_changed(
        self,
        current_row: int,
        current_column: int,
        previous_row: int,
        previous_column: int,
    ):
        Context.focus_card_changed.emit(CubeableFocusEvent(self.item(current_row, 2).cubeable))

    def _on_round_started(self, draft_round: DraftRound) -> None:
        self._current_pack = draft_round.pack

    def _on_picked(
        self,
        pick_point: PickPoint,
        target: t.Tuple[t.Optional[CubeScene], t.Optional[QtCore.QPoint]],
        new: bool,
    ) -> None:
        self.insertRow(0)
        self.setItem(
            0,
            0,
            QtWidgets.QTableWidgetItem(str(self._current_pack)),
        )
        self.setItem(
            0,
            1,
            QtWidgets.QTableWidgetItem(str(pick_point.pick_number)),
        )
        if isinstance(pick_point.pick, SinglePickPick):
            self.setItem(
                0,
                2,
                CubeableTableItem(pick_point.pick.cubeable),
            )
        elif isinstance(pick_point.pick, BurnPick):
            self.setItem(
                0,
                2,
                CubeableTableItem(pick_point.pick.pick),
            )
            if pick_point.pick.burn is not None:
                self.setItem(
                    0,
                    3,
                    CubeableTableItem(pick_point.pick.burn),
                )
        self.setItem(
            0,
            4,
            QtWidgets.QTableWidgetItem(
                ', '.join(
                    (
                        cubeable.cardboard.name
                        if isinstance(cubeable, Printing) else
                        cubeable.description
                    )
                    for cubeable in
                    pick_point.booster.cubeables
                )
            ),
        )
        self.resizeColumnsToContents()


class BotsView(QtWidgets.QWidget):
    picked = pyqtSignal(object, bool)

    def __init__(
        self,
        draft_model: DraftModel,
    ) -> None:
        super().__init__()
        self._draft_model = draft_model

        self._active = False
        self._active_button = QtWidgets.QPushButton('activate')
        self._active_button.clicked.connect(self._activate_toggle)

        self._mode_picker = QtWidgets.QComboBox()
        self._mode_picker.addItems(('Pick', 'Recommend'))

        self._delay_pick = QtWidgets.QSpinBox()
        self._delay_pick.setRange(0, 60)

        self._bots = collect_bots()
        self._bot_picker = QtWidgets.QComboBox()
        self._bot_picker.addItems(self._bots)

        self._executor: t.Optional[ThreadPoolExecutor] = None
        self._pending_pick: t.Optional[Future] = None

        self._draft_model.received_booster.connect(self._submit_booster)

        layout = QtWidgets.QHBoxLayout(self)

        options_layout = QtWidgets.QFormLayout()

        options_layout.addWidget(self._active_button)
        options_layout.addRow('mode', self._mode_picker)
        options_layout.addRow('delay', self._delay_pick)

        bot_select_layout = QtWidgets.QVBoxLayout()

        bot_select_layout.addWidget(self._bot_picker)

        layout.addLayout(options_layout)
        layout.addLayout(bot_select_layout)

    def _activate_toggle(self) -> None:
        if self._active:
            self.deactivate()
        else:
            self.activate()

    def deactivate(self) -> None:
        if not self._active:
            return

        self._active = False
        self._active_button.setText('activate')
        if self._pending_pick is not None:
            self._pending_pick.cancel()
            self._pending_pick = None

    def _on_bot_complete(self, pick: Cubeable, booster: DraftBooster) -> None:
        if booster == self._draft_model.draft_client.history.current.booster and self._active:
            self.picked.emit(pick, self._mode_picker.currentText() == 'Recommend')

    def _submit_booster(self, pick_point: PickPoint) -> None:
        if not self._active:
            return

        self._pending_pick = self._executor.submit(
            bot_pick,
            self._bots[self._bot_picker.currentText()],
            pick_point.booster,
            self._draft_model.draft_client.pool,
            self._delay_pick.value(),
            self._on_bot_complete,
        )

    def activate(self) -> None:
        if self._active:
            return

        if self._mode_picker.currentText() == 'Pick':
            confirm_dialog = QMessageBox()
            confirm_dialog.setText('Confirm bot draft')
            confirm_dialog.setInformativeText(
                'You sure you want to activate bot with mode: {}?'.format(self._mode_picker.currentText())
            )
            confirm_dialog.setStandardButtons(QMessageBox.No | QMessageBox.Yes)
            confirm_dialog.setDefaultButton(QMessageBox.No)
            return_code = confirm_dialog.exec_()

            if return_code == QMessageBox.No:
                return

        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers = 3)

        self._active = True
        self._active_button.setText('deactivate')

        current_booster = self._draft_model.draft_client.history.current

        if current_booster is not None and self._pending_pick is None:
            self._submit_booster(current_booster)


class DraftView(Editable):

    def __init__(
        self,
        draft_model: DraftModel,
        *,
        pool_view: t.Optional[PoolView] = None,
    ) -> None:
        super().__init__()
        self._draft_model = draft_model

        self._booster_widget = BoosterWidget(draft_model)

        self._pool_model = PoolModel() if pool_view is None else pool_view.pool_model

        self._bottom_tabs = QtWidgets.QTabWidget()

        self._pool_view = PoolView(self._pool_model) if pool_view is None else pool_view
        self._picks_table = PicksTable(self._draft_model)
        self._bots_view = BotsView(self._draft_model)

        self._bottom_tabs.addTab(self._pool_view, 'pool')
        self._bottom_tabs.addTab(self._picks_table, 'picks')
        self._bottom_tabs.addTab(self._bots_view, 'bots')

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 1)

        self._splitter.addWidget(self._booster_widget)
        self._splitter.addWidget(self._bottom_tabs)

        layout.addWidget(self._splitter)

        self._draft_model.draft_started.connect(self._on_draft_started)
        self._draft_model.picked.connect(self._on_picked)
        self._draft_model.draft_completed.connect(self._on_draft_completed)
        self._bots_view.picked.connect(self._on_bot_picked)

        self._draft_model.connect()

    @property
    def pool_model(self) -> PoolModel:
        return self._pool_model

    # @property
    # def booster_widget(self) -> BoosterWidget:
    #     return self._booster_widget

    @property
    def draft_model(self) -> DraftModel:
        return self._draft_model

    def _on_draft_started(self, draft_configuration: DraftConfiguration) -> None:
        if issubclass(draft_configuration.draft_format, Burn):
            self._bottom_tabs.setTabEnabled(self._bottom_tabs.indexOf(self._bots_view), False)

        self._pool_model.infinites = draft_configuration.infinites

    def _on_bot_picked(self, pick: Cubeable, recommend: bool):
        if recommend:
            found = False
            for card in self._booster_widget.booster_scene.items():
                if not found and card.cubeable == pick:
                    card.set_highlight(QColor(0, 0, 255, 100))
                    found = True
                else:
                    card.clear_highlight()
        else:
            for card in self._booster_widget.booster_scene.items():
                if card.cubeable == pick:
                    self._draft_model.pick(card)
                    return

    def _on_picked(
        self,
        pick: PickPoint,
        target: t.Tuple[t.Optional[CubeScene], t.Optional[QtCore.QPoint]],
        new: bool,
    ) -> None:
        if not new:
            return

        self._pool_view.undo_stack.clear()

        scene, position = target

        release_id = (
            pick.round.booster_specification.release.id
            if isinstance(pick.round.booster_specification, CubeBoosterSpecification) else
            None
        )

        (self._pool_view.pool_model.pool if scene is None else scene).get_cube_modification(
            add = [
                PhysicalCard.from_cubeable(cubeable, release_id = release_id)
                for cubeable in
                pick.pick.added_cubeables
            ],
            closed_operation = True,
            position = position,
        ).redo()

    def _on_draft_completed(self, pool_id: int, session_name: str):
        if self._draft_model.draft_client.draft_configuration.reverse:
            Context.sealed_started.emit(pool_id, True)
        else:
            Context.sealed_started.emit(pool_id, False)
            Context.editor.add_editable(
                self._pool_view,
                EditablesMeta(
                    session_name,
                    key = session_name,
                ),
            )
        Context.editor.close_editable(self)

    def close(self) -> None:
        self._draft_model.close()

    @property
    def undo_stack(self) -> QUndoStack:
        return self._pool_view.undo_stack

    def is_empty(self) -> bool:
        return False

    def persist(self) -> t.Any:
        return {
            'pool_view': self._pool_view.persist(),
            'splitter': self._splitter.saveState(),
            'draft_model': self._draft_model.persist(),
        }

    @classmethod
    def load(cls, state: t.Any) -> DraftView:
        draft_view = cls(
            draft_model = DraftModel.load(state['draft_model']),
            pool_view = PoolView.load(state['pool_view']),
        )
        draft_view._splitter.restoreState(state['splitter'])
        return draft_view
