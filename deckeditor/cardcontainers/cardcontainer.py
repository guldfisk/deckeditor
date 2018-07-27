import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore

from mtgorp.models.persistent.printing import Printing
from mtgorp.models.collections.serilization.strategy import JsonId
from mtgorp.db.static import MtgDb

from deckeditor.cardcontainers.alignment.curser import Cursor
from deckeditor.cardcontainers.alignment.aligner import Aligner, Direction, CardScene
from deckeditor.cardcontainers.alignment.stackinggrids.staticstackinggrid import StaticStackingGrid
from deckeditor.cardcontainers.physicalcard import PhysicalCard
from deckeditor.containers.magic import CardPackage
from deckeditor.undo.command import UndoStack, UndoCommand
from deckeditor.values import DeckZone
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


class ChangeAligner(UndoCommand):

	def __init__(self, scene: 'CardScene', aligner: Aligner):
		self._scene = scene
		self._aligner = aligner
		self._previous_aligner = None #type: t.Optional[Aligner]
		self._cards = [] #type: t.List[PhysicalCard]
		self._positions = [] #type: t.List[QtCore.QPointF]
		self._detach = None #type: UndoCommand
		self._attach = None #type: UndoCommand

	def setup(self):
		self._previous_aligner = self._scene.aligner
		self._cards = list(self._scene.items())
		self._positions = list(
			item.pos() for item in self._cards
		)
		self._detach = self._scene.aligner.detach_cards(self._cards)
		self._detach.setup()
		self._attach = self._aligner.attach_cards(self._cards, QtCore.QPointF(0, 0))
		self._attach.setup()

	def redo(self) -> None:
		self._detach.redo()
		self._scene.aligner = self._aligner
		self._attach.redo()

	def undo(self) -> None:
		self._attach.undo()
		self._scene.aligner = self._previous_aligner
		self._detach.undo()


class CardContainer(QtWidgets.QGraphicsView):
	serialization_strategy = JsonId(MtgDb.db)

	def __init__(
		self,
		undo_stack: UndoStack,
		aligner: t.Type[Aligner] = StaticStackingGrid,
	):
		self._card_scene = CardScene(aligner, undo_stack)

		super().__init__(self._card_scene)

		self._zones = None #type: t.Dict[DeckZone, CardContainer]

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

		self._card_scene.aligner.cursor_moved.connect(lambda pos: self.centerOn(pos))

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
				self._zones[DeckZone.MAINDECK],
			),
			'Alt+1',
		)
		self._move_selected_to_sideboard_action = self._create_action(
			'Move Selected to Sideboard',
			lambda : self._move_cards_to_scene(
				self.card_scene.selectedItems(),
				self._zones[DeckZone.SIDEBOARD],
			),
			'Alt+2',
		)
		self._move_selected_to_pool_action = self._create_action(
			'Move Selected to Pool',
			lambda : self._move_cards_to_scene(
				self.card_scene.selectedItems(),
				self._zones[DeckZone.POOL],
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

	def set_zones(self, zones: t.Dict[DeckZone, 'CardContainer']):
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
			self._card_scene.aligner.move_cursor(Direction.UP, key_event.modifiers())

		elif pressed_key == QtCore.Qt.Key_Right:
			self._card_scene.aligner.move_cursor(Direction.RIGHT, key_event.modifiers())

		elif pressed_key == QtCore.Qt.Key_Down:
			self._card_scene.aligner.move_cursor(Direction.DOWN, key_event.modifiers())

		elif pressed_key == QtCore.Qt.Key_Left:
			self._card_scene.aligner.move_cursor(Direction.LEFT, key_event.modifiers())

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
		if drag_event.source() is not None and isinstance(drag_event.source(), CardContainer):
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

	def mouseDoubleClickEvent(self, click_event: QtGui.QMouseEvent):
		pass
		# item = self.itemAt(click_event.pos()) #type: PhysicalCard
		#
		# if item is None:
		# 	return
		#
		# item.mouseDoubleClickEvent(click_event)

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
				mime = QtCore.QMimeData()
				stream = QtCore.QByteArray()

				stream.append(
					self.serialization_strategy.serialize(
						CardPackage(
							card.printing
							for card in
							self._floating
						)
					)
				)

				mime.setData('cards', stream)
				drag.setMimeData(mime)
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

				if item is not None and isinstance(item, PhysicalCard):
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