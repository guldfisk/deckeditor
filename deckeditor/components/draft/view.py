from __future__ import annotations

import threading
import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QMouseEvent
from PyQt5.QtWidgets import QUndoStack, QGraphicsItem, QAbstractItemView

from mtgorp.db.database import CardDatabase

from magiccube.collections.cubeable import Cubeable

from cubeclient.models import ApiClient

from mtgdraft.client import DraftClient, SinglePick, Burn
from mtgdraft.models import Booster, DraftRound, Pick, SinglePickPick, BurnPick

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


class _DraftClient(DraftClient):

    def __init__(self, api_client: ApiClient, draft_id: str, db: CardDatabase, draft_model: DraftModel):
        super().__init__(api_client, draft_id, db)
        self._draft_model = draft_model

    def _received_booster(self, booster: Booster) -> None:
        self._draft_model.received_booster.emit(booster)

    def _picked(self, pick: Pick, pick_number: int, booster: Booster) -> None:
        self._draft_model.on_pick(pick, pick_number, booster)

    def _completed(self, pool_id: int, session_name: str) -> None:
        self._draft_model.draft_completed.emit(pool_id, session_name)

    def _on_start(self) -> None:
        self._draft_model.draft_started.emit()

    def _on_round(self, draft_round: DraftRound) -> None:
        self._draft_model.round_started.emit(draft_round)


class DraftModel(QObject):
    connected = pyqtSignal(bool)
    received_booster = pyqtSignal(Booster)
    cubeable_picked = pyqtSignal(object, tuple, Booster, bool)
    draft_started = pyqtSignal()
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

        self._pick: t.Optional[PhysicalCard] = None
        self._burn: t.Optional[PhysicalCard] = None
        self._booster: t.Optional[Booster] = None

        self.received_booster.connect(self._on_received_booster)

    def _on_received_booster(self, booster: Booster) -> None:
        self._booster = booster

    def on_pick(self, pick: Pick, pick_number: int, booster: Booster) -> None:
        new = True
        with self._pick_number_lock:
            if pick_number <= self._pick_number:
                new = False
            else:
                self._pick_number = pick_number

        self.cubeable_picked.emit(
            (
                pick.cubeable
                if isinstance(pick, SinglePickPick) else
                pick.pick
            ),
            (self._pending_picked_scene, self._pending_picked_position),
            booster,
            new,
        )
        self._pending_picked_scene = None
        self._pending_picked_position = None

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
                self._burn.set_highlight(QColor(255, 0, 0, 100))
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
                self._pick.set_highlight(QColor(0, 255, 0, 100))
                self._pending_picked_position = position
                self._pending_picked_scene = scene

            if self._pick and (self._burn or self._booster is not None and len(self._booster.cubeables) == 1):
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

        if item and isinstance(item, PhysicalCard):
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

        menu.addAction(self._fit_action)

        sort_menu = menu.addMenu('Sort')

        for action in self._sort_actions:
            sort_menu.addAction(action)

        select_menu = menu.addMenu('Select')

        for action in (
            self._select_all_action,
            self._selection_search_action,
            self._deselect_all_action,
        ):
            select_menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))


class BoosterWidget(QtWidgets.QWidget):

    def __init__(self, draft_model: DraftModel):
        super().__init__()
        self._undo_stack = Context.get_undo_stack()

        self._draft_model = draft_model

        self._players_list = QtWidgets.QLabel()
        self._players_list.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self._pack_counter_label = QtWidgets.QLabel()
        self._pick_counter_label = QtWidgets.QLabel()
        self._booster_scene = CubeScene(GridAligner, mode = CubeEditMode.CLOSED)
        self._booster_view = CubeView(
            scene = self._booster_scene,
            undo_stack = self._undo_stack,
            cube_image_view = BoosterImageView(
                self._undo_stack,
                self._booster_scene,
                self._draft_model,
            )
        )

        layout = QtWidgets.QVBoxLayout(self)

        info_bar_layout = QtWidgets.QHBoxLayout()

        info_bar_layout.addWidget(self._players_list)
        info_bar_layout.addWidget(self._pack_counter_label)
        info_bar_layout.addWidget(self._pick_counter_label)

        layout.addLayout(info_bar_layout)
        layout.addWidget(self._booster_view)

        self._draft_model.received_booster.connect(self._on_receive_booster)
        self._draft_model.cubeable_picked.connect(self._on_cubeable_picked)
        self._draft_model.round_started.connect(self._on_round_started)
        self._booster_view.cube_image_view.card_double_clicked.connect(self._on_card_double_clicked)

    def _on_card_double_clicked(self, card: PhysicalCard, modifiers: Qt.KeyboardModifiers):
        self._draft_model.pick(
            card = card,
            burn = modifiers == Qt.ShiftModifier,
            infer = True,
            toggle = True,
        )

    def _on_round_started(self, draft_round: DraftRound) -> None:
        self._players_list.setText(
            'Draft order: ' + (
                ' -> '
                if draft_round.clockwise else
                ' <- '
            ).join(
                drafter.username
                for drafter in
                self._draft_model.draft_client.drafters
            )
        )
        self._pack_counter_label.setText(
            'Pack: {}/{}'.format(
                draft_round.pack,
                sum(
                    spec.amount
                    for spec in
                    self._draft_model.draft_client.pool_specification.booster_specifications
                ),
            )
        )

    def _on_receive_booster(self, booster: Booster) -> None:
        self._booster_view.cube_image_view.cancel_drags()
        self._booster_scene.get_cube_modification(
            add = list(
                map(
                    PhysicalCard.from_cubeable,
                    booster.cubeables,
                )
            ),
            remove = self._booster_scene.items(),
            closed_operation = True,
        ).redo()

    def _on_cubeable_picked(
        self,
        cubeable: Cubeable,
        target: t.Tuple[t.Optional[CubeScene], t.Optional[QtCore.QPoint]],
        booster: Booster,
        new: bool,
    ) -> None:
        self._booster_scene.get_cube_modification(
            remove = self._booster_scene.items(),
            closed_operation = True,
        ).redo()


class PicksTable(QtWidgets.QTableWidget):

    def __init__(self, draft_model: DraftModel):
        super().__init__(0, 4)

        self._draft_model = draft_model

        self.setHorizontalHeaderLabels(
            (
                'Pack',
                'Pick Number',
                'Pick',
                'Burn',
            )
        )

        self.setMouseTracking(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._current_pack = 0

        self.currentCellChanged.connect(self._handle_current_cell_changed)

        self._draft_model.round_started.connect(self._on_round_started)
        self._draft_model.cubeable_picked.connect(self._on_cubeable_picked)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        item = self.itemAt(event.pos())
        if item is not None:
            Context.focus_card_changed.emit(self.item(item.row(), 2).cubeable)

    def _handle_current_cell_changed(
        self,
        current_row: int,
        current_column: int,
        previous_row: int,
        previous_column: int,
    ):
        Context.focus_card_changed.emit(self.item(current_row, 2).cubeable)

    def _on_round_started(self, draft_round: DraftRound) -> None:
        self._current_pack = draft_round.pack

    def _on_cubeable_picked(
        self,
        cubeable: Cubeable,
        target: t.Tuple[t.Optional[CubeScene], t.Optional[QtCore.QPoint]],
        booster: Booster,
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
            QtWidgets.QTableWidgetItem(str(booster.pick)),
        )
        self.setItem(
            0,
            2,
            CubeableTableItem(cubeable),
        )
        self.resizeColumnsToContents()


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

        self._bottom_tabs.addTab(self._pool_view, 'pool')
        self._bottom_tabs.addTab(self._picks_table, 'picks')

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        layout = QtWidgets.QVBoxLayout(self)

        self._splitter.addWidget(self._booster_widget)
        self._splitter.addWidget(self._bottom_tabs)

        layout.addWidget(self._splitter)

        self._draft_model.connect()
        self._draft_model.cubeable_picked.connect(self._on_cubeable_picked)
        self._draft_model.draft_completed.connect(self._on_draft_completed)

    @property
    def pool_model(self) -> PoolModel:
        return self._pool_model

    def _on_cubeable_picked(
        self,
        cubeable: Cubeable,
        target: t.Tuple[t.Optional[CubeScene], t.Optional[QtCore.QPoint]],
        booster: Booster,
        new: bool,
    ) -> None:
        if not new:
            return

        self._pool_view.undo_stack.clear()

        scene, position = target

        (self._pool_view.pool_model.pool if scene is None else scene).get_cube_modification(
            add = (PhysicalCard.from_cubeable(cubeable),),
            closed_operation = True,
            position = position,
        ).redo()

    def _on_draft_completed(self, pool_id: int, session_name: str):
        Context.sealed_started.emit(pool_id)
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
