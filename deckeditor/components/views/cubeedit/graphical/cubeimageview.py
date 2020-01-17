from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoStack, QGraphicsItem

from magiccube.collections.delta import CubeDeltaOperation
from magiccube.laps.traps.trap import Trap
from magiccube.laps.traps.tree.printingtree import AllNode, AnyNode, BorderedNode
from mtgorp.models.persistent.printing import Printing
from mtgorp.tools.parsing.exceptions import ParseException
from mtgorp.tools.search.extraction import PrintingStrategy
from mtgorp.tools.search.pattern import Criteria

from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.context.context import Context
from deckeditor.sorting.sort import SortProperty
from yeetlong.multiset import Multiset


class QueryEdit(QtWidgets.QLineEdit):

    def keyPressEvent(self, key_press: QtGui.QKeyEvent):
        if key_press.key() == QtCore.Qt.Key_Return or key_press.key() == QtCore.Qt.Key_Enter:
            self.parent().compile()

        else:
            super().keyPressEvent(key_press)


class SearchSelectionDialog(QtWidgets.QDialog):

    def __init__(self, parent: CubeImageView):
        super().__init__(parent)

        self._query_edit = QueryEdit(self)

        self._error_label = QtWidgets.QLabel()
        self._error_label.hide()

        self._box = QtWidgets.QVBoxLayout()

        self._box.addWidget(self._query_edit)
        self._box.addWidget(self._error_label)

        self.setLayout(self._box)

    def compile(self):
        try:
            self.parent().search_select.emit(
                Context.search_pattern_parser.parse_criteria(
                    self._query_edit.text()
                )
            )
            self.accept()
        except ParseException as e:
            self._error_label.setText(str(e))
            self._error_label.show()
            return


class CubeImageView(QtWidgets.QGraphicsView):
    # serialization_strategy = JsonId(MtgDb.db)
    search_select = QtCore.pyqtSignal(Criteria)

    def __init__(
        self,
        undo_stack: QUndoStack,
        # aligner: t.Type[Aligner] = StaticStackingGrid,
        scene: CubeScene,
    ):
        self._scene = scene
        super().__init__(scene)
        self._undo_stack = undo_stack

        self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self._rubber_band = QtWidgets.QRubberBand(
            QtWidgets.QRubberBand.Rectangle,
            self
        )
        self._rubber_band.hide()
        self._rubber_band_origin = QtCore.QPoint()

        self._floating: t.List[PhysicalCard] = []
        self._dragging: t.List[PhysicalCard] = []

        self._dragging_move: bool = False
        self._last_move_event_pos = None

        self.scale(.3, .3)

        # self._card_scene.cursor_moved.connect(lambda pos: self.centerOn(pos))
        #
        self._sort_actions: t.List[QtWidgets.QAction] = []

        self._create_sort_action_pair(SortProperty.CMC, 'm')
        self._create_sort_action_pair(SortProperty.COLOR, 'l')
        self._create_sort_action_pair(SortProperty.RARITY, 'r')
        self._create_sort_action_pair(SortProperty.TYPE, 't')
        self._create_sort_action_pair(SortProperty.NAME, 'n')
        self._create_sort_action_pair(SortProperty.EXPANSION)
        self._create_sort_action_pair(SortProperty.COLLECTOR_NUMBER)
        #
        self._fit_action = self._create_action('Fit View', self._fit_all_cards, 'Ctrl+I')
        self._select_all_cards_action = self._create_action('Select All', lambda: self._scene.select_all(), 'Ctrl+A')
        self._deselect_all_action = self._create_action(
            'Deselect All',
            lambda: self._scene.clear_selection(),
            'Ctrl+D',
        )
        self._selection_search_action = self._create_action(
            'Select Matching',
            self._search_select,
            'Ctrl+E',
        )
        #
        # self._move_selected_to_maindeck_action = self._create_action(
        #     'Move Selected to Maindeck',
        #     lambda : self._move_cards_to_scene(
        #         self.card_scene.selectedItems(),
        #         self._zones[DeckZoneType.MAINDECK],
        #     ),
        #     'Alt+1',
        # )
        # self._move_selected_to_sideboard_action = self._create_action(
        #     'Move Selected to Sideboard',
        #     lambda : self._move_cards_to_scene(
        #         self.card_scene.selectedItems(),
        #         self._zones[DeckZoneType.SIDEBOARD],
        #     ),
        #     'Alt+2',
        # )
        # self._move_selected_to_pool_action = self._create_action(
        #     'Move Selected to Pool',
        #     lambda : self._move_cards_to_scene(
        #         self.card_scene.selectedItems(),
        #         self._zones[DeckZoneType.POOL],
        #     ),
        #     'Alt+3',
        # )
        #
        self.customContextMenuRequested.connect(self._context_menu_event)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.search_select.connect(self._on_search_select)

    def _search_select(self) -> None:
        dialog = SearchSelectionDialog(self)
        dialog.exec()

    def _on_search_select(self, criteria: Criteria) -> None:
        self._scene.set_selection(
            item
            for item in
            self._scene.items()
            if isinstance(item.cubeable, Printing) and criteria.match(item.cubeable, PrintingStrategy)
        )

    def _create_sort_action_pair(
        self,
        sort_property: SortProperty,
        short_cut_letter: t.Optional[str] = None,
    ) -> None:
        self._create_sort_action(sort_property, QtCore.Qt.Horizontal, short_cut_letter)
        self._create_sort_action(sort_property, QtCore.Qt.Vertical, short_cut_letter)

    def _create_sort_action(
        self,
        sort_property: SortProperty,
        orientation: int,
        short_cut_letter: t.Optional[str] = None,
    ) -> None:

        self._sort_actions.append(
            self._create_action(
                f'Sort {sort_property.value} {"Horizontally" if orientation == QtCore.Qt.Horizontal else "Vertically"}',
                lambda: self._undo_stack.push(
                    self._scene.aligner.sort(
                        sort_property,
                        orientation,
                    )
                ),
                None
                if short_cut_letter is None else
                f'Ctrl+{"Shift" if orientation == QtCore.Qt.Vertical else "Alt"}+{short_cut_letter}'
            )
        )

    @property
    def floating(self) -> t.List[PhysicalCard]:
        return self._floating

    def _create_action(self, name: str, result: t.Callable, shortcut: t.Optional[str] = None) -> QtWidgets.QAction:
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(result)

        if shortcut:
            action.setShortcut(shortcut)
            action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.addAction(action)

        return action

    @property
    def dragging(self) -> t.List[PhysicalCard]:
        return self._dragging

    # @property
    # def keyboard_cursor(self) -> Cursor:
    #     return self._cursor
    #
    # @property
    # def undo_stack(self) -> UndoStack:
    #     return self._undo_stack
    #
    @property
    def cube_scene(self) -> CubeScene:
        return self._scene

    # def set_zones(self, zones: t.Dict[DeckZoneType, 'CardContainer']):
    #     self._zones = zones

    # def _move_cards_to_scene(
    #     self,
    #     cards: t.Iterable[PhysicalCard],
    #     target: 'CardContainer',
    # ):
    #     cards = list(cards)
    #     self._undo_stack.push(
    #         self._card_scene.aligner.detach_cards(cards),
    #         self._card_scene.aligner.remove_cards(cards),
    #     )
    #
    #     target.undo_stack.push(
    #         target._card_scene.aligner.attach_cards(cards)
    #     )
    #
    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        pressed_key = key_event.key()
        modifiers = key_event.modifiers()

        # if pressed_key == QtCore.Qt.Key_Up:
        #     self._card_scene.aligner.move_cursor(Direction.UP, modifiers)
        #
        # elif pressed_key == QtCore.Qt.Key_Right:
        #     self._card_scene.aligner.move_cursor(Direction.RIGHT, modifiers)
        #
        # elif pressed_key == QtCore.Qt.Key_Down:
        #     self._card_scene.aligner.move_cursor(Direction.DOWN, modifiers)
        #
        # elif pressed_key == QtCore.Qt.Key_Left:
        #     self._card_scene.aligner.move_cursor(Direction.LEFT, modifiers)
        #
        # elif pressed_key == QtCore.Qt.Key_Plus:
        #     self.scale(1.1, 1.1)
        #
        # elif pressed_key == QtCore.Qt.Key_Minus:
        #     self.scale(.9, .9)

        if pressed_key == QtCore.Qt.Key_Delete:
            cards = self._scene.selectedItems()
            if cards:
                Context.undo_group.activeStack().push(
                    self._scene.get_cube_scene_remove(
                        cards
                    )
                )

        # elif pressed_key == QtCore.Qt.Key_Period:
        #     pos = self.mapFromScene(self.card_scene.cursor.pos())
        #     self.customContextMenuRequested.emit(
        #         QtCore.QPoint(
        #             int(pos.x()),
        #             int(pos.y()),
        #         )
        #     )

        else:
            super().keyPressEvent(key_event)

    def _fit_all_cards(self) -> None:
        self.fitInView(self._scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)

    def _get_flatten_trap(self, card: PhysicalCard[Trap]) -> t.Callable[[], None]:
        def _flatten_trap():
            self._undo_stack.push(
                self._scene.get_cube_modification(
                    (
                        list(
                            map(
                                PhysicalCard,
                                (
                                    child if isinstance(child, Printing) else Trap(child)
                                    for child in
                                    card.cubeable.node.flattened
                                ),
                            )
                        ),
                        (card,),
                    ),
                    card.pos() + QPoint(1, 1),
                )
            )

        return _flatten_trap

    def _get_select_or(self, card: PhysicalCard[Trap], child: t.Union[BorderedNode, Printing]):
        def _select_or():
            self._undo_stack.push(
                self._scene.get_cube_modification(
                    (
                        list(
                            map(
                                PhysicalCard,
                                (child,)
                                if isinstance(child, Printing) else
                                (
                                    _child if isinstance(_child, Printing) else Trap(_child)
                                    for _child in
                                    child.flattened
                                )
                            )
                        ),
                        (card,),
                    ),
                    card.pos() + QPoint(1, 1),
                )
            )

        return _select_or

    def _context_menu_event(self, position: QtCore.QPoint):
        menu = QtWidgets.QMenu(self)

        menu.addAction(self._fit_action)

        sort_menu = menu.addMenu('Sort')

        for action in self._sort_actions:
            sort_menu.addAction(action)

        menu.addSeparator()

        item: QGraphicsItem = self.itemAt(position)

        if item and isinstance(item, PhysicalCard):

            if isinstance(item.cubeable, Trap):

                if isinstance(item.cubeable.node, AllNode):
                    flatten = QtWidgets.QAction('Flatten', menu)
                    flatten.triggered.connect(self._get_flatten_trap(item))
                    menu.addAction(flatten)

                elif isinstance(item.cubeable.node, AnyNode):
                    flatten = menu.addMenu('Flatten')

                    for child in item.cubeable.node.children:
                        _flatten = QtWidgets.QAction(str(child), flatten)
                        _flatten.triggered.connect(self._get_select_or(item, child))
                        flatten.addAction(_flatten)

            elif isinstance(item.cubeable, Printing):

                if item.cubeable.cardboard.back_cards:
                    transform = QtWidgets.QAction('Transform', menu)
                    transform.triggered.connect(self.flip)
                    menu.addAction(transform)

        menu.exec_(self.mapToGlobal(position))

    def dragEnterEvent(self, drag_event: QtGui.QDragEnterEvent):
        if isinstance(drag_event.source(), self.__class__):
            # if drag_event.source() == self:
            drag_event.accept()
        # print(drag_event.source())
        # drag_event.accept()

    def dragMoveEvent(self, drag_event: QtGui.QDragMoveEvent):
        pass

    def dropEvent(self, drop_event: QtGui.QDropEvent):
        print('drop', self._floating, drop_event.source())
        if drop_event.source() == self:
            if self._floating:
                self._undo_stack.push(
                    self._scene.get_intra_move(
                        self._floating,
                        self.mapToScene(
                            drop_event.pos()
                        ),
                    )
                )
                self._floating[:] = []
        else:
            self._undo_stack.push(
                drop_event.source().cube_scene.get_inter_move(
                    drop_event.source().floating,
                    self._scene,
                    self.mapToScene(
                        drop_event.pos()
                    )
                )
            )
        # self._undo_stack.push(
        #     InterTransferCubeModels(
        #         drop_event.source().cube_scene.cube_model,
        #         self._scene.cube_model,
        #         CubeDeltaOperation(
        #             Multiset(
        #                 card.cubeable
        #                 for card in
        #                 drop_event.source().dragging
        #             ).elements()
        #         )
        #     )
        # )
        # drop_event.setDropAction(QtCore.Qt.MoveAction)
        # drop_event.accept()
        # self._undo_stack.push(
        #     self._card_scene.aligner.attach_cards(
        #         drop_event.source().dragging,
        #         self.mapToScene(
        #             drop_event.pos()
        #         ),
        #     )
        # )

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        modifiers = event.modifiers()
        if (
            modifiers & QtCore.Qt.ControlModifier
            or Context.settings.value('image_view_scroll_default_zoom', True, bool)
        ):
            transform = self.transform()
            x_scale, y_scale = transform.m11(), transform.m22()
            delta = event.angleDelta().y() / 2000
            x_scale, y_scale = [
                max(.1, min(4, scale + delta))
                for scale in
                (x_scale, y_scale)
            ]
            old_position = self.mapToScene(event.pos())
            self.resetTransform()
            self.scale(x_scale, y_scale)
            new_position = self.mapToScene(event.pos())
            position_delta = new_position - old_position
            self.translate(position_delta.x(), position_delta.y())
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, mouse_event: QtGui.QMouseEvent):
        if (
            mouse_event.button() == QtCore.Qt.LeftButton and mouse_event.modifiers() & QtCore.Qt.ControlModifier
            or mouse_event.button() == QtCore.Qt.MiddleButton
        ):
            self._dragging_move = True

        elif mouse_event.button() == QtCore.Qt.LeftButton:
            item = self.itemAt(mouse_event.pos())

            if item is None:
                self._scene.clear_selection()

            else:
                if not item.isSelected():
                    self._scene.set_selection((item,))

                self._floating = self.scene().selectedItems()
                # self._scene.pick_up(self._floating)

                drag = QtGui.QDrag(self)
                mime = QtCore.QMimeData()
                stream = QtCore.QByteArray()

                mime.setData('cards', stream)
                drag.setMimeData(mime)
                drag.setPixmap(self._floating[-1].pixmap().scaledToWidth(100))

                exec_value = drag.exec_()

                # if exec_value != QtCore.Qt.MoveAction:
                #     self._scene.drop(self._dragging, mouse_event.pos())
                #     for card in self._dragging:
                #         card.show()
                #     self._dragging[:] = []
                #
                print('drag returning', exec_value)

    def mouseMoveEvent(self, mouse_event: QtGui.QMouseEvent):
        if self._last_move_event_pos:
            delta = mouse_event.globalPos() - self._last_move_event_pos
        else:
            delta = None

        self._last_move_event_pos = mouse_event.globalPos()

        if self._dragging_move:
            if delta:
                transform = self.transform()
                x_scale, y_scale = transform.m11(), transform.m22()
                self.translate(delta.x() / x_scale, delta.y() / y_scale)

        elif self._rubber_band.isHidden():

            # # if mouse_event.buttons() & QtCore.Qt.LeftButton:
            #
            # if not QtCore.QRectF(
            #     0,
            #     0,
            #     self.size().width(),
            #     self.size().height(),
            # ).contains(
            #     mouse_event.pos()
            # ):
            #     drag = QtGui.QDrag(self)
            #     mime = QtCore.QMimeData()
            #     stream = QtCore.QByteArray()
            #
            #     mime.setData('cards', stream)
            #     drag.setMimeData(mime)
            #     drag.setPixmap(self._floating[-1].pixmap().scaledToWidth(100))
            #
            #     # self._undo_stack.push(
            #     #     self._card_scene.aligner.remove_cards(
            #     #         self._floating,
            #     #     )
            #     # )
            #
            #     for card in self._floating:
            #         card.hide()
            #
            #     self._dragging[:] = self._floating[:]
            #     self._floating[:] = []
            #     exec_value = drag.exec_()
            #
            #     if exec_value != QtCore.Qt.MoveAction:
            #         self._scene.drop(self._dragging, mouse_event.pos())
            #         for card in self._dragging:
            #             card.show()
            #         self._dragging[:] = []
            #
            #     print('drag returning', exec_value)
            #
            # elif self._floating:
            #     for item in self._floating:
            #         item.setPos(self.mapToScene(mouse_event.pos()))
            #
            # else:
            item = self.itemAt(mouse_event.pos())

            if isinstance(item, PhysicalCard):
                Context.focus_card_changed.emit(item.cubeable)

            if mouse_event.buttons():
                self._rubber_band_origin = mouse_event.pos()
                self._rubber_band.setGeometry(
                    QtCore.QRect(
                        self._rubber_band_origin,
                        QtCore.QSize(),
                    )
                )
                self._rubber_band.show()

        else:
            self._rubber_band.setGeometry(
                QtCore.QRect(
                    self._rubber_band_origin,
                    mouse_event.pos(),
                ).normalized()
            )

    def mouseReleaseEvent(self, mouse_event: QtGui.QMouseEvent):
        self._dragging_move = False

        if not mouse_event.button() == QtCore.Qt.LeftButton:
            return

        if self._rubber_band.isHidden():
            # if self._floating:
            #     # self._undo_stack.push(
            #     #     self._card_scene.aligner.attach_cards(
            #     #         self._floating,
            #     #         self.mapToScene(
            #     #             mouse_event.pos()
            #     #         ),
            #     #     )
            #     # )
            #     self._scene.drop(
            #         self._floating,
            #         self.mapToScene(
            #             mouse_event.pos()
            #         )
            #     )
            #     self._floating[:] = []

            return

        self._rubber_band.hide()

        self._scene.add_selection(
            self.scene().items(
                self.mapToScene(
                    self._rubber_band.geometry()
                )
            )
        )
