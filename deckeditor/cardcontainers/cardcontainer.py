import pickle

import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore

from mtgorp.models.persistent.printing import Printing
from mtgorp.models.collections.serilization.strategy import JsonId
from mtgorp.db.static import MtgDb

from deckeditor.cardcontainers.alignment.stackinggrid import StackingGrid
from deckeditor.cardcontainers.alignment.grid import GridAligner
from deckeditor.cardcontainers.alignment.aligner import Aligner
from deckeditor.cardcontainers.physicalcard import PhysicalCard
from deckeditor.containers.magic import CardPackage
from deckeditor.undo.command import UndoStack, UndoCommand


class SelectionChange(UndoCommand):
	pass


class SetSelected(SelectionChange):

	def __init__(self, scene: 'CardScene', cards: t.Iterable[PhysicalCard]):
		self._cards = list(cards)
		self._previous = list(scene.selectedItems())

	def redo(self) -> None:
		for card in self._previous:
			card.setSelected(False)

		for card in self._cards:
			card.setSelected(True)

	def undo(self) -> None:
		for card in self._cards:
			card.setSelected(False)

		for card in self._previous:
			card.setSelected(True)

	def ignore(self) -> bool:
		return not (self._cards or self._previous)


class AddSelected(SelectionChange):

	def __init__(self, cards: t.Iterable[PhysicalCard]):
		self._cards = list(
			card
			for card in
			cards
			if not card.isSelected()
		)

	def redo(self) -> None:
		for card in self._cards:
			card.setSelected(True)

	def undo(self) -> None:
		for card in self._cards:
			card.setSelected(False)

	def ignore(self) -> bool:
		return not self._cards


class Deselect(SelectionChange):

	def __init__(self, cards: t.Iterable[PhysicalCard]):
		self._cards = list(
			card
			for card in
			cards
			if card.isSelected()
		)

	def redo(self) -> None:
		for card in self._cards:
			card.setSelected(False)

	def undo(self) -> None:
		for card in self._cards:
			card.setSelected(True)

	def ignore(self) -> bool:
		return not self._cards


class PositiveSelectionIntersection(SelectionChange):

	def __init__(self, scene: 'CardScene', cards: t.Iterable[PhysicalCard]):
		_cards = set(cards)
		self._cards = list(
			card
			for card in
			scene.selectedItems()
			if not card in _cards
		)

	def redo(self) -> None:
		for card in self._cards:
			card.setSelected(False)

	def undo(self) -> None:
		for card in self._cards:
			card.setSelected(True)

	def ignore(self) -> bool:
		return not self._cards


class NegativeSelectionIntersection(SelectionChange):

	def __init__(self, scene: 'CardScene', cards: t.Iterable[PhysicalCard]):
		_cards = set(cards)
		self._cards = list(
			card
			for card in
			scene.selectedItems()
			if card in _cards
		)

	def redo(self) -> None:
		for card in self._cards:
			card.setSelected(False)

	def undo(self) -> None:
		for card in self._cards:
			card.setSelected(True)

	def ignore(self) -> bool:
		return not self._cards


class ClearSelection(SelectionChange):

	def __init__(self, scene: 'CardScene'):
		self._scene = scene
		self._deselected = scene.selectedItems()

	def redo(self) -> None:
		self._scene.clearSelection()

	def undo(self) -> None:
		for card in self._deselected:
			card.setSelected(True)

	def ignore(self) -> bool:
		return not self._deselected


class AddPrintings(UndoCommand):

	def __init__(self, scene: 'CardScene', printings: t.Iterable[Printing], target: QtCore.QPointF):
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
		for card in self._cards:
			self._scene.removeItem(card)

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


class CardScene(QtWidgets.QGraphicsScene):

	def __init__(self, aligner_type: t.Type[Aligner] = StackingGrid):
		super().__init__()
		self._aligner = aligner_type(self)

	@property
	def aligner(self) -> Aligner:
		return self._aligner

	@aligner.setter
	def aligner(self, aligner: Aligner) -> None:
		self._aligner = aligner


class CardContainer(QtWidgets.QGraphicsView):
	serialization_strategy = JsonId(MtgDb.db)

	def __init__(self, undo_stack: UndoStack, aligner: t.Type[Aligner] = StackingGrid):
		self._graphic_scene = CardScene(aligner)
		super().__init__(self._graphic_scene)

		self._undo_stack = undo_stack

		self.setAcceptDrops(True)

		self._rubber_band = QtWidgets.QRubberBand(
			QtWidgets.QRubberBand.Rectangle,
			self
		)
		self._rubber_band.hide()
		self._rubber_band_origin = QtCore.QPoint()

		self._floating = [] #type: t.List[PhysicalCard]
		self._dragging = [] #type: t.List[PhysicalCard]

	@property
	def dragging(self) -> t.List[PhysicalCard]:
		return self._dragging

	def dragEnterEvent(self, drag_event: QtGui.QDragEnterEvent):
		if drag_event.source() is not None and isinstance(drag_event.source(), CardContainer):
			drag_event.accept()

	def dragMoveEvent(self, drag_event: QtGui.QDragMoveEvent):
		pass

	def dropEvent(self, drop_event: QtGui.QDropEvent):
		self._undo_stack.push(
			self._graphic_scene.aligner.attach_cards(
				drop_event.source().dragging,
				self.mapToScene(
					drop_event.pos()
				),
			)
		)

	def mousePressEvent(self, press_event: QtGui.QMouseEvent):
		item = self.itemAt(press_event.pos())

		if item is not None:
			if not item.isSelected():
				self._undo_stack.push(
					SetSelected(self.scene(), (item,))
				)

			self._floating = self.scene().selectedItems()
			self._undo_stack.push(
				self._graphic_scene.aligner.detach_cards(self._floating)
			)
			return

		self._undo_stack.push(
			ClearSelection(self.scene())
		)

	def mouseDoubleClickEvent(self, click_event: QtGui.QMouseEvent):
		item = self.itemAt(click_event.pos()) #type: PhysicalCard

		if item is None:
			return

		item.mouseDoubleClickEvent(click_event)

	def mouseMoveEvent(self, move_event: QtGui.QMouseEvent):
		if self._rubber_band.isHidden():

			if not QtCore.QRectF(
				0,
				0,
				self.size().width(),
				self.size().height(),
			).contains(
				move_event.pos()
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
					self._graphic_scene.aligner.remove_cards(
						self._floating,
					)
				)

				self._dragging[:] = self._floating[:]
				self._floating[:] = []
				drag.exec_()

				return

			if self._floating:
				for item in self._floating:
					item.setPos(self.mapToScene(move_event.pos()))

			else:
				self._rubber_band_origin = move_event.pos()
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
					move_event.pos(),
				).normalized()
			)

	def mouseReleaseEvent(self, release_event: QtGui.QMouseEvent):
		if self._rubber_band.isHidden():
			if self._floating:
				self._undo_stack.push(
					self._graphic_scene.aligner.attach_cards(
						self._floating,
						self.mapToScene(
							release_event.pos()
						),
					)
				)
				self._floating[:] = []

			return

		self._rubber_band.hide()

		self._undo_stack.push(
			AddSelected(
				self.scene().items(
					self.mapToScene(
						self._rubber_band.geometry()
					)
				)
			)
		)