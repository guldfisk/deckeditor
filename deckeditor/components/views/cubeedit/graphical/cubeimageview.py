from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QPoint, Qt, QRectF, QRect
from PyQt5.QtGui import QPainter, QPolygonF, QTransform
from PyQt5.QtWidgets import QUndoStack, QGraphicsItem, QAction

from yeetlong.multiset import Multiset

from mtgorp.models.persistent.printing import Printing
from mtgorp.models.serilization.strategies.picklestrategy import PickleStrategy
from mtgorp.tools.parsing.exceptions import ParseException
from mtgorp.tools.search.extraction import PrintingStrategy
from mtgorp.tools.search.pattern import Criteria

from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.components.views.cubeedit.graphical.sortdialog import SortDialog
from deckeditor.utils.undo import CommandPackage
from deckeditor.models.cubes.physicalcard import PhysicalCard, PhysicalAllCard
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.context.context import Context
from deckeditor.sorting import sorting
from deckeditor.components.cardview.focuscard import CubeableFocusEvent
from deckeditor.utils.actions import WithActions
from deckeditor.sorting.sorting import SortProperty
from deckeditor.utils.transform import serialize_transform, transform_factory


class QueryEdit(QtWidgets.QLineEdit):

    def keyPressEvent(self, key_press: QtGui.QKeyEvent):
        if key_press.key() == QtCore.Qt.Key_Return or key_press.key() == QtCore.Qt.Key_Enter:
            self.parent().compile()

        else:
            super().keyPressEvent(key_press)


class SearchSelectionDialog(QtWidgets.QDialog):

    def __init__(self, parent: CubeImageView):
        super().__init__(parent)
        self.setWindowTitle('Select Matching')

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


class CubeImageView(QtWidgets.QGraphicsView, WithActions):
    search_select = QtCore.pyqtSignal(Criteria)
    card_double_clicked = QtCore.pyqtSignal(PhysicalCard, int)

    def __init__(self, undo_stack: QUndoStack, scene: CubeScene):
        super().__init__(scene)

        self._scene = scene
        self._undo_stack = undo_stack

        self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.setRenderHints(QPainter.SmoothPixmapTransform)

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
        self._last_press_on_card = False
        self._last_double_click = False
        self._drag = None

        self._sort_actions: t.MutableMapping[t.Tuple[t.Type[SortProperty], int], QtWidgets.QAction] = {}

        self._create_sort_action_pair(sorting.ColorExtractor, 'o')
        self._create_sort_action_pair(sorting.ColorIdentityExtractor, 'i')
        self._create_sort_action_pair(sorting.CMCExtractor, 'm')
        self._create_sort_action_pair(sorting.NameExtractor, 'n')
        self._create_sort_action_pair(sorting.IsLandExtractor, 'l')
        self._create_sort_action_pair(sorting.IsCreatureExtractor, 't')
        self._create_sort_action_pair(sorting.CubeableTypeExtractor)
        self._create_sort_action_pair(sorting.CubeableTypeExtractor)
        self._create_sort_action_pair(sorting.IsMonoExtractor)
        self._create_sort_action_pair(sorting.RarityExtractor)
        self._create_sort_action_pair(sorting.ExpansionExtractor)
        self._create_sort_action_pair(sorting.CollectorNumberExtractor)

        self._fit_action = self._create_action('Fit View', self._fit_cards, 'F')
        self._select_all_action = self._create_action('Select All', lambda: self._scene.select_all(), 'Ctrl+A')
        self._sort_action = self._create_action('Sort', self._sort, 'Alt+S')
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
        self._create_action('Copy', self._copy, 'Ctrl+C')
        self._create_action('Paste', self._paste, 'Ctrl+V')

        self.customContextMenuRequested.connect(self._context_menu_event)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.search_select.connect(self._on_search_select)

        self.setTransform(QTransform())
        self.scale(.3, .3)

        self._selected_info_text = ''

        self._scene.selectionChanged.connect(self._update_selected_info_text)
        self._scene.changed.connect(self._update_selected_info_text)

    def _update_status(self) -> None:
        Context.status_message.emit(self._scene.name + ' ' + self._selected_info_text, 0)

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)
        self._update_status()

    def _update_selected_info_text(self, *args, **kwargs) -> None:
        self._selected_info_text = (
            '{}/{}'.format(
                len(self._scene.selectedItems()),
                len(self._scene.items()),
            )
        )
        self._update_status()
        if Context.settings.value('on_view_card_count', True, bool):
            self.update()

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @undo_stack.setter
    def undo_stack(self, stack: QUndoStack) -> None:
        self._undo_stack = stack

    def _paste(self):
        mime = Context.clipboard.mimeData()
        cards = mime.data('cards')

        if not cards:
            return

        cube = PickleStrategy(Context.db).deserialize(Cube, cards)

        self._undo_stack.push(
            self._scene.get_cube_modification(
                CubeDeltaOperation(cube.cubeables.elements()),
                QPoint() if self._last_move_event_pos is None else self.mapToScene(self._last_move_event_pos),
            )
        )

    def _copy(self):
        cards = self._scene.selectedItems()

        if not cards:
            return

        stream = QtCore.QByteArray(
            PickleStrategy.serialize(
                Cube(
                    card.cubeable
                    for card in
                    cards
                )
            )
        )

        mime = QtCore.QMimeData()

        mime.setData('cards', stream)

        Context.clipboard.setMimeData(mime)

    def _on_sort_selected(
        self,
        sort_property: t.Type[sorting.SortProperty],
        orientation: int,
        respect_custom: bool,
    ) -> None:
        self._undo_stack.push(
            self._scene.aligner.sort(
                sort_property,
                self._scene.items() if not self._scene.selectedItems() else self._scene.selectedItems(),
                orientation,
                bool(self._scene.selectedItems()),
            )
        )

    def _sort(self) -> None:
        dialog = SortDialog.get()
        dialog.selection_done.connect(self._on_sort_selected)
        dialog.exec_()
        dialog.selection_done.disconnect(self._on_sort_selected)

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
        sort_property: t.Type[sorting.SortProperty],
        short_cut_letter: t.Optional[str] = None,
    ) -> None:
        self._create_sort_action(sort_property, QtCore.Qt.Horizontal, short_cut_letter)
        self._create_sort_action(sort_property, QtCore.Qt.Vertical, short_cut_letter)

    def _create_sort_action(
        self,
        sort_property: t.Type[sorting.SortProperty],
        orientation: int,
        short_cut_letter: t.Optional[str] = None,
    ) -> None:
        self._sort_actions[sort_property, orientation] = (
            self._create_action(
                f'{sort_property.name} {"Horizontally" if orientation == QtCore.Qt.Horizontal else "Vertically"}',
                lambda: self._on_sort_selected(sort_property, orientation, True),
                None
                if short_cut_letter is None else
                f'Ctrl+{"Shift" if orientation == QtCore.Qt.Vertical else "Alt"}+{short_cut_letter}'
            )
        )

    @property
    def floating(self) -> t.List[PhysicalCard]:
        return self._floating

    @property
    def dragging(self) -> t.List[PhysicalCard]:
        return self._dragging

    @property
    def cube_scene(self) -> CubeScene:
        return self._scene

    def mouseDoubleClickEvent(self, click_event: QtGui.QMouseEvent) -> None:
        modifiers = click_event.modifiers()

        item = self.itemAt(click_event.pos())
        if isinstance(item, PhysicalCard):
            if modifiers & QtCore.Qt.ControlModifier:
                cubeable_extractor = (
                    (lambda c: c.cubeable.cardboard if isinstance(c.cubeable, Printing) else c.cardboard)
                    if Context.settings.value('doubleclick_match_on_cardboards', True, bool) else
                    (lambda c: c.cubeable)
                )
                for card in self._scene.items():
                    if cubeable_extractor(card) == cubeable_extractor(item):
                        card.setSelected(True)
                self._last_double_click = True
            else:
                self.card_double_clicked.emit(item, modifiers)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        pressed_key = key_event.key()
        modifiers = key_event.modifiers()

        # TODO is there a reason this isnt actions?
        if pressed_key == QtCore.Qt.Key_Delete:
            cards = self._scene.selectedItems()
            if cards:
                self._undo_stack.push(
                    self._scene.get_cube_modification(
                        remove = cards
                    )
                )

        elif (
            pressed_key == QtCore.Qt.Key_J
            and modifiers & QtCore.Qt.ControlModifier
        ):
            cards = self._scene.selectedItems()
            if cards:
                self._undo_stack.push(
                    self._scene.get_cube_modification(
                        CubeDeltaOperation(
                            Multiset(
                                card.cubeable
                                for card in
                                cards
                            ).elements()
                        ),
                        cards[0].pos() + QPoint(1, 1),
                    )
                )
        else:
            super().keyPressEvent(key_event)

    def _fit_cards(self) -> None:
        selected = (
            None
            if Context.settings.value('fit_all_cards', False, bool) else
            self._scene.selectedItems()
        )
        if selected:
            rect = QRectF(selected[0].pos(), selected[0].boundingRect().size())
            if len(selected) > 1:
                for item in selected[1:]:
                    rect |= QRectF(item.pos(), item.boundingRect().size())
            self.fitInView(
                rect,
                QtCore.Qt.KeepAspectRatio,
            )
        else:
            self.fitInView(
                self._scene.itemsBoundingRect(),
                QtCore.Qt.KeepAspectRatio,
            )

    def get_persistable_transform(self) -> QTransform:
        current_transform = self.transform()
        transform = transform_factory(
            horizontal_scaling_factor = current_transform.m11(),
            vertical_scaling_factor = current_transform.m22(),
        )
        p = self.mapToScene(QPoint())
        transform.translate(-p.x(), -p.y())
        return transform

    def _flatten_all_traps(self) -> None:
        selected = None if Context.settings.value('always_flatten_all', False, bool) else self._scene.selectedItems()
        self._undo_stack.push(
            CommandPackage(
                [
                    card.get_flatten_command(Context.settings.value('flatten_recursively', True, bool))
                    for card in (selected if selected else self._scene.items())
                    if isinstance(card, PhysicalAllCard)
                ]
            )
        )

    def _context_menu_event(self, position: QtCore.QPoint):
        menu = QtWidgets.QMenu(self)

        menu.addAction(self._fit_action)

        sort_menu = menu.addMenu('Sort')

        for (_, orientation), action in self._sort_actions.items():
            if orientation == QtCore.Qt.Horizontal or self._scene.aligner.supports_sort_orientation:
                sort_menu.addAction(action)

        select_menu = menu.addMenu('Select')

        for action in (
            self._select_all_action,
            self._selection_search_action,
            self._deselect_all_action,
        ):
            select_menu.addAction(action)

        flatten_all = QAction('Flatten All', menu)
        flatten_all.triggered.connect(self._flatten_all_traps)
        menu.addAction(flatten_all)

        menu.addSeparator()

        item: QGraphicsItem = self.itemAt(position)

        if item and isinstance(item, PhysicalCard):
            menu.addSeparator()

            item.context_menu(menu, self._undo_stack)

        menu.addSeparator()

        self._scene.aligner.context_menu(menu, self.mapToScene(position), self._undo_stack)

        menu.exec_(self.mapToGlobal(position))

    def dragEnterEvent(self, drag_event: QtGui.QDragEnterEvent):
        if isinstance(drag_event.source(), self.__class__):
            drag_event.accept()

    def dragMoveEvent(self, drag_event: QtGui.QDragMoveEvent):
        pass

    def successful_drop(self, drop_event: QtGui.QDropEvent, image_view: CubeImageView) -> bool:
        return True

    def dropEvent(self, drop_event: QtGui.QDropEvent):
        drop_event.acceptProposedAction()
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
        elif (
            isinstance(drop_event.source(), self.__class__)
            and drop_event.source().successful_drop(
            drop_event,
            self,
        )
        ):
            self._undo_stack.push(
                drop_event.source().cube_scene.get_inter_move(
                    drop_event.source().floating,
                    self._scene,
                    self.mapToScene(
                        drop_event.pos()
                    )
                )
            )

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
        self._last_move_event_pos = None

        if (
            mouse_event.button() == QtCore.Qt.LeftButton and mouse_event.modifiers() & QtCore.Qt.ControlModifier
            or mouse_event.button() == QtCore.Qt.MiddleButton
        ):
            self._dragging_move = True

        elif mouse_event.button() == QtCore.Qt.LeftButton:
            item = self.itemAt(mouse_event.pos())

            if item is None:
                if mouse_event.modifiers() == Qt.NoModifier:
                    self._scene.clear_selection()
                self._last_press_on_card = False

            else:
                if not item.isSelected():
                    self._scene.set_selection((item,), mouse_event.modifiers())

                self._last_press_on_card = True

    def cancel_drags(self) -> None:
        if self._drag is not None:
            self._drag.cancel()

    def mouseMoveEvent(self, mouse_event: QtGui.QMouseEvent):
        Context.focus_scene_changed.emit(self._scene)

        if self._last_press_on_card:
            if mouse_event.buttons() & Qt.LeftButton and mouse_event.modifiers() == Qt.NoModifier:
                self._floating = self.scene().selectedItems()
                if not self._floating:
                    return

                drag = QtGui.QDrag(self)
                mime = QtCore.QMimeData()
                stream = QtCore.QByteArray()

                mime.setData('cards', stream)
                drag.setMimeData(mime)
                drag.setPixmap(self._floating[-1].pixmap().scaledToWidth(100))
                self._drag = drag
                drag.exec_()
                self._drag = None
                return
            else:
                self._last_press_on_card = False

        if self._last_move_event_pos:
            delta = mouse_event.pos() - self._last_move_event_pos
        else:
            delta = None

        self._last_move_event_pos = mouse_event.pos()

        if self._dragging_move:
            if delta:
                transform = self.transform()
                x_scale, y_scale = transform.m11(), transform.m22()
                self.translate(delta.x() / x_scale, delta.y() / y_scale)

        elif self._rubber_band.isHidden():
            item = self.itemAt(mouse_event.pos())

            if isinstance(item, PhysicalCard):
                card_mapped_position = self.mapToScene(mouse_event.pos()) - item.pos()

                Context.focus_card_changed.emit(
                    CubeableFocusEvent(
                        cubeable = item.cubeable,
                        size = (
                            item.boundingRect().width(),
                            item.boundingRect().height(),
                        ),
                        position = (
                            card_mapped_position.x(),
                            card_mapped_position.y(),
                        ),
                        modifiers = mouse_event.modifiers()
                    )
                )

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
        modifiers = mouse_event.modifiers()
        self._dragging_move = False

        if not mouse_event.button() == QtCore.Qt.LeftButton:
            return

        if self._rubber_band.isHidden():
            if self._last_move_event_pos is None:
                if self._last_double_click:
                    self._last_double_click = False
                else:
                    item = self.itemAt(mouse_event.pos())
                    if item is not None:
                        self._scene.set_selection((item,), modifiers)
            return

        self._rubber_band.hide()

        potential_items = self.scene().items(
            self.mapToScene(
                self._rubber_band.geometry()
            )
        )

        if Context.settings.value('select_on_covered_parts', False, bool):
            self._scene.add_selection(potential_items, modifiers)
            return

        cards = []
        rubber_band_polygon = QPolygonF(
            self.mapToScene(
                self._rubber_band.geometry()
            )
        )

        covered_polygon = None

        for card in potential_items:
            rect = QRectF(card.boundingRect())
            rect.translate(card.pos())

            if rubber_band_polygon.intersects(
                QPolygonF(rect).subtracted(covered_polygon)
                if covered_polygon is not None else
                QPolygonF(rect)
            ):
                cards.append(card)

            current_cover_area = QPolygonF(
                QRectF(
                    rect.x() - 1,
                    rect.y() - 1,
                    rect.width() + 2,
                    rect.height() + 2,
                )
            )

            if covered_polygon is None:
                covered_polygon = current_cover_area
            else:
                covered_polygon = covered_polygon.united(current_cover_area)

        self._scene.add_selection(cards, modifiers)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)

        if not Context.settings.value('on_view_card_count', True, bool):
            return

        rect = self.rect()

        text = self._selected_info_text

        font = QtGui.QFont()
        font.setPointSize(16)
        metric = QtGui.QFontMetrics(font, self)

        painter = QtGui.QPainter(self.viewport())
        color = QtGui.QColor(self.backgroundBrush().color())
        color.setAlpha(127)

        text_rect = QRect(
            rect.width() - metric.horizontalAdvance(text) - 50,
            20,
            metric.horizontalAdvance(text),
            font.pointSize(),
        )

        painter.fillRect(text_rect, color)

        painter.setPen(QtGui.QColor(200, 200, 200))
        painter.setFont(font)
        painter.drawText(text_rect.x(), text_rect.y() + text_rect.height(), text)

        painter.setClipRect(text_rect)
