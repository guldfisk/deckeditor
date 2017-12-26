
import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore

from cardcontainers.card import Card



class CardScene(QtWidgets.QGraphicsScene):
	def __init__(self):
		super().__init__()
		self._card_stackers = {} #type: t.Dict[t.Tuple[int, int], CardStacker]
		self._card_stacker_width = 1000
		self._card_stacker_height = 1400
	def get_card_stacker(self, x, y):
		key = x // self._card_stacker_width, y // self._card_stacker_height
		try:
			return self._card_stackers[key]
		except KeyError:
			self._card_stackers[key] = CardStacker(
				(key[0]*self._card_stacker_width,
				 key[1]*self._card_stacker_height)
			)
			return self._card_stackers[key]

class CardContainer(QtWidgets.QGraphicsView):
	def __init__(self):
		self._graphic_scene = CardScene()
		super().__init__(self._graphic_scene)
		self.setAcceptDrops(True)

		self._rubber_band = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
		self._rubber_band.hide()
		self._rubber_band_origin = QtCore.QPoint()

		self._floating = [] #type: t.List[Card]

		printing = Globals.db.cardboards['Bloodghast'].from_expansion('ZEN')
		another_printing = Globals.db.cardboards['Dive Down'].from_expansion('XLN')
		for i in range(100):
			card = Card(printing)
			self._graphic_scene.addItem(
				card
			)
			card.moveBy(40, 40)
			self._graphic_scene.addItem(Card(another_printing))

	def dragEnterEvent(self, drag_event: QtGui.QDragEnterEvent):
		if drag_event.source() is not None and isinstance(drag_event.source(), CardContainer):
			drag_event.accept()
	def dragMoveEvent(self, drag_event: QtGui.QDragMoveEvent):
		pass
	def dropEvent(self, drop_event: QtGui.QDropEvent):
		print('drop event', self._floating)
		if drop_event.source()==self:
			for item in self.scene().selectedItems():
				item.align(self.mapToScene(drop_event.pos()))
		else:
			for item in drop_event.source().scene().selectedItems():
				self.scene().addItem(item)
				item.align(self.mapToScene(drop_event.pos()))

	def mousePressEvent(self, press_event: QtGui.QMouseEvent):
		super().mousePressEvent(press_event)
		item = self.itemAt(press_event.pos())
		if not item:
			for item in self.scene().selectedItems():
				item.setSelected(False)
			self._rubber_band_origin = press_event.pos()
			self._rubber_band.setGeometry(QtCore.QRect(self._rubber_band_origin, QtCore.QSize()))
			self._rubber_band.show()
		else:
			self._floating = self.scene().selectedItems()
	def mouseMoveEvent(self, move_event: QtGui.QMouseEvent):
		super().mouseMoveEvent(move_event)
		if self._rubber_band.isHidden():
			if not QtCore.QRectF(
				0,
				0,
				self.size().width(),
				self.size().height()
			).contains(
				move_event.pos()
			):
				drag = QtGui.QDrag(self)
				mime = QtCore.QMimeData()
				stream = QtCore.QByteArray()
				stream.append(
					pickle.dumps(
						tuple(
							card.printing.cardboard.name
							for card in
							self._floating
						)
					)
				)
				mime.setData('cards', stream)
				drag.setMimeData(mime)
				self._floating[:] = []
				drag.exec_()
			elif self._floating:
				for item in self._floating:
					item.setPos(self.mapToScene(move_event.pos()))
		else:
			self._rubber_band.setGeometry(
				QtCore.QRect(self._rubber_band_origin, move_event.pos()).normalized()
			)
	def mouseReleaseEvent(self, release_event: QtGui.QMouseEvent):
		super().mouseReleaseEvent(release_event)
		if self._rubber_band.isHidden():
			if self._floating:
				for item in self._floating:
					item.align(
						self.mapToScene(
							release_event.pos()
						)
					)
				self._floating[:] = []
		else:
			self._rubber_band.hide()
			for item in self.scene().items(
				self.mapToScene(
					self._rubber_band.geometry()
				)
			):
				item.setSelected(True)
