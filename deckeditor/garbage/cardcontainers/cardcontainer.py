import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore

from mtgorp.models.persistent.printing import Printing
from mtgorp.models.serilization.strategies.jsonid import JsonId
from mtgorp.db.static import MtgDb

from deckeditor.garbage.cardcontainers.alignment import Cursor
from deckeditor.garbage.cardcontainers.alignment import Aligner, Direction, CardScene
from deckeditor.garbage.cardcontainers.alignment import StaticStackingGrid
from deckeditor.garbage.cardcontainers.physicalcard import PhysicalCard
from deckeditor.garbage.undo import UndoStack, UndoCommand
from deckeditor.values import DeckZoneType
from deckeditor.values import SortProperty
from deckeditor.context.context import Context


class AddPrintings(UndoCommand):

	def __init__(self, scene: 'CardScene', printings: t.Iterable[Printing], target: QtCore.QPointF = None):
		self._scene = scene
		self._printings = printings
		self._cards = None #type: t.List[PhysicalCard]
		self._target = target
		self._attach = None #type: UndoCommand

	def setup(self):
		self._cards = [PhysicalCard(printing) for printing in self._printings]
		self._attach = self._scene.aligner.attach_cards(self._cards, self._target)
		self._attach.setup()

	def redo(self) -> None:
		self._attach.redo()

	def undo(self) -> None:
		self._attach.undo()
		self._scene.remove_cards(*self._cards)

	def ignore(self) -> bool:
		return not self._printings


class CardContainer(QtWidgets.QGraphicsView):
	serialization_strategy = JsonId(MtgDb.db)

	def __init__(
		self,
		undo_stack: UndoStack,
		aligner: t.Type[Aligner] = StaticStackingGrid,
	):
		self._card_scene = CardScene(aligner, undo_stack)

		super().__init__(self._card_scene)

		self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

		self._zones = None #type: t.Dict[DeckZoneType, CardContainer]

		self._undo_stack = undo_stack

		self.setAcceptDrops(True)
		self.setMouseTracking(True)

		self._rubber_band = QtWidgets.QRubberBand(
			QtWidgets.QRubberBand.Rectangle,
			self
		)
		self._rubber_band.hide()
		self._rubber_band_origin = QtCore.QPoint()

		self._floating = [] #type: t.List[PhysicalCard]
		self._dragging = [] #type: t.List[PhysicalCard]

		self._card_scene.cursor_moved.connect(lambda pos: self.centerOn(pos))

		self._sort_actions = [] #type: t.List[QtWidgets.QAction]

		self._create_sort_action_pair(SortProperty.CMC, 'm')
		self._create_sort_action_pair(SortProperty.COLOR, 'l')
		self._create_sort_action_pair(SortProperty.RARITY, 'r')
		self._create_sort_action_pair(SortProperty.TYPE, 't')
		self._create_sort_action_pair(SortProperty.NAME, 'n')
		self._create_sort_action_pair(SortProperty.EXPANSION)
		self._create_sort_action_pair(SortProperty.COLLECTOR_NUMBER)

		self._fit_action = self._create_action('Fit View', self._fit_all_cards, 'Ctrl+i')

		self._move_selected_to_maindeck_action = self._create_action(
			'Move Selected to Maindeck',
			lambda : self._move_cards_to_scene(
				self.card_scene.selectedItems(),
				self._zones[DeckZoneType.MAINDECK],
			),
			'Alt+1',
		)
		self._move_selected_to_sideboard_action = self._create_action(
			'Move Selected to Sideboard',
			lambda : self._move_cards_to_scene(
				self.card_scene.selectedItems(),
				self._zones[DeckZoneType.SIDEBOARD],
			),
			'Alt+2',
		)
		self._move_selected_to_pool_action = self._create_action(
			'Move Selected to Pool',
			lambda : self._move_cards_to_scene(
				self.card_scene.selectedItems(),
				self._zones[DeckZoneType.POOL],
			),
			'Alt+3',
		)

		self.customContextMenuRequested.connect(self._context_menu_event)
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

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
					self.card_scene.aligner.sort(
						sort_property,
						orientation,
					)
				),
				None
				if short_cut_letter is None else
				f'Ctrl+{"Shift" if orientation == QtCore.Qt.Vertical else "Alt"}+{short_cut_letter}'
			)
		)

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

	@property
	def keyboard_cursor(self) -> Cursor:
		return self._cursor

	@property
	def undo_stack(self) -> UndoStack:
		return self._undo_stack

	@property
	def card_scene(self) -> CardScene:
		return self._card_scene

	def set_zones(self, zones: t.Dict[DeckZoneType, 'CardContainer']):
		self._zones = zones

	def _move_cards_to_scene(
		self,
		cards: t.Iterable[PhysicalCard],
		target: 'CardContainer',
	):
		cards = list(cards)
		self._undo_stack.push(
			self._card_scene.aligner.detach_cards(cards),
			self._card_scene.aligner.remove_cards(cards),
		)

		target.undo_stack.push(
			target._card_scene.aligner.attach_cards(cards)
		)

	def keyPressEvent(self, key_event: QtGui.QKeyEvent):
		pressed_key = key_event.key()
		modifiers = key_event.modifiers()

		if pressed_key == QtCore.Qt.Key_Up:
			self._card_scene.aligner.move_cursor(Direction.UP, modifiers)

		elif pressed_key == QtCore.Qt.Key_Right:
			self._card_scene.aligner.move_cursor(Direction.RIGHT, modifiers)

		elif pressed_key == QtCore.Qt.Key_Down:
			self._card_scene.aligner.move_cursor(Direction.DOWN, modifiers)

		elif pressed_key == QtCore.Qt.Key_Left:
			self._card_scene.aligner.move_cursor(Direction.LEFT, modifiers)

		elif pressed_key == QtCore.Qt.Key_Plus:
			self.scale(1.1, 1.1)

		elif pressed_key == QtCore.Qt.Key_Minus:
			self.scale(.9, .9)

		elif pressed_key == QtCore.Qt.Key_Delete:
			cards = self._card_scene.selectedItems()
			self._undo_stack.push(
				self._card_scene.aligner.detach_cards(cards),
				self._card_scene.aligner.remove_cards(cards),
			)

		elif pressed_key == QtCore.Qt.Key_Period:
			pos = self.mapFromScene(self.card_scene.cursor.pos())
			self.customContextMenuRequested.emit(
				QtCore.QPoint(
					int(pos.x()),
					int(pos.y()),
				)
			)

		else:
			super().keyPressEvent(key_event)

	def _fit_all_cards(self) -> None:
		self.fitInView(self._card_scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)

	def _context_menu_event(self, position: QtCore.QPoint):
		menu = QtWidgets.QMenu(self)

		menu.addAction(self._fit_action)

		sort_menu = menu.addMenu('Sort')

		for action in self._sort_actions:
			sort_menu.addAction(action)

		menu.addSeparator()

		item = self.itemAt(position)

		if item and isinstance(item, PhysicalCard):
			item.context_menu(menu)

		menu.exec_(self.mapToGlobal(position))

	def dragEnterEvent(self, drag_event: QtGui.QDragEnterEvent):
		if isinstance(drag_event.source(), CardContainer):
			drag_event.accept()

	def dragMoveEvent(self, drag_event: QtGui.QDragMoveEvent):
		pass

	def dropEvent(self, drop_event: QtGui.QDropEvent):
		self._undo_stack.push(
			self._card_scene.aligner.attach_cards(
				drop_event.source().dragging,
				self.mapToScene(
					drop_event.pos()
				),
			)
		)

	def mousePressEvent(self, mouse_event: QtGui.QMouseEvent):
		if not mouse_event.button() == QtCore.Qt.LeftButton:
			return

		item = self.itemAt(mouse_event.pos())

		if item is not None:

			if not item.isSelected():
				self._card_scene.set_selection((item,))

			self._floating = self.scene().selectedItems()
			self._undo_stack.push(
				self._card_scene.aligner.detach_cards(self._floating)
			)
			return

		self._card_scene.clear_selection()

	def mouseMoveEvent(self, mouse_event: QtGui.QMouseEvent):
		if self._rubber_band.isHidden():

			if not QtCore.QRectF(
				0,
				0,
				self.size().width(),
				self.size().height(),
			).contains(
				mouse_event.pos()
			):
				drag = QtGui.QDrag(self)
				# mime = QtCore.QMimeData()
				# stream = QtCore.QByteArray()
				#
				# mime.setData('cards', stream)
				# drag.setMimeData(mime)
				drag.setPixmap(self._floating[-1].pixmap().scaledToWidth(100))

				self._undo_stack.push(
					self._card_scene.aligner.remove_cards(
						self._floating,
					)
				)

				self._dragging[:] = self._floating[:]
				self._floating[:] = []
				drag.exec_()

				return

			if self._floating:
				for item in self._floating:
					item.setPos(self.mapToScene(mouse_event.pos()))

			else:
				item = self.itemAt(mouse_event.pos())

				if isinstance(item, PhysicalCard):
					Context.card_view.set_image.emit(item.image_request())

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
		if not mouse_event.button() == QtCore.Qt.LeftButton:
			return

		if self._rubber_band.isHidden():
			if self._floating:
				self._undo_stack.push(
					self._card_scene.aligner.attach_cards(
						self._floating,
						self.mapToScene(
							mouse_event.pos()
						),
					)
				)
				self._floating[:] = []

			return

		self._rubber_band.hide()

		self._card_scene.add_selection(
			self.scene().items(
				self.mapToScene(
					self._rubber_band.geometry()
				)
			)
		)