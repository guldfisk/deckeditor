

from PyQt5 import QtWidgets, QtGui, QtCore

from mtgorp.models.persistent import printing as _printing
from mtgorp.db.static import MtgDb

from pixmapload.pixmaploader import PixmapLoader
from cardcontainers.cardcontainer import CardStacker

class Card(QtWidgets.QGraphicsObject):
	signal = QtCore.pyqtSignal(object)

	# noinspection PyCallByClass
	def __init__(self, printing: _printing.Printing):
		super().__init__()

		self._selection_highlite_pen = QtGui.QPen(
			QtGui.QColor(255, 0, 0),
			QtCore.QSettings().value('card_selected_frame_width', 5),
		)

		self._printing = printing

		self._set_image(self._printing)

		self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
		self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)

		self._card_stacker = None  # type: CardStacker

	@property
	def card_stacker(self):
		return self._card_stacker

	@card_stacker.setter
	def card_stacker(self, card_stacker: 'CardStacker'):
		self._card_stacker = card_stacker

	@property
	def printing(self):
		return self._printing

	def boundingRect(self):
		return self._bounding_rect

	def _set_image(self, printing: '_printing.Printing'):
		pixmap_promise = ImageLoader.get_pixmap(printing)
		if pixmap_promise.is_fulfilled:
			self.setPixmap(pixmap_promise.get())
		else:
			self.setPixmap(ImageLoader.get_default_pixmap().get())
			self.signal.connect(self._set_pixmap)
			pixmap_promise.then(self.signal.emit)

	def _set_pixmap(self, pixmap: QPixmap):
		self.setPixmap(pixmap)
		self.update()

	def align(self, pos: QtCore.QPointF):
		self.scene().get_card_stacker(pos.x(), pos.y()).add_card(self)

	def mouseDoubleClickEvent(self, *args, **kwargs):
		print('double clicked')
		ImageLoader.get_pixmap(Globals.db.cardboards['Lightning Bolt'].from_expansion('LEA')).then(self._set_pixmap)
# def mouseReleaseEvent(self, event):
# 	super().mouseReleaseEvent(event)
# 	print('mouse release event', self, event.pos(), self.scene())
# 	print(self.scene().get_card_stacker(event.scenePos().x(), event.scenePos().y()))
# 	for item in self.scene().selectedItems():
# 		if isinstance(item, Card):
# 			item.align(event.scenePos())
# def mousePressEvent(self, event):
# 	super().mousePressEvent(event)
# 	print('mouse pressed', self, event, self.scene().selectedItems())
# 	for item in self.scene().selectedItems():
# 		print(item.card_stacker)
# 		if isinstance(item, Card) and item.card_stacker is not None:
# 			print('lets go', item.card_stacker.cards)
# 			print(item)
# 			item.card_stacker.remove_card(item)
# 			print('card removed')
# def itemChange(self, change, value):
# 	# super().itemChange(change, value)
# 	# if change==QtWidgets.QGraphicsItem.ItemSelectedChange and value:
# 	# 	self.move_to_top()
# 	if change==QtWidgets.QGraphicsItem.ItemSceneChange:
# 		if self._card_stacker is not None:
# 			self._card_stacker.remove_card(self)
# 	# if change==QtWidgets.QGraphicsItem.ItemPositionHasChanged:
# 	# 	print('position change', value)
# 	# return QtWidgets.QGraphicsItem.itemChange(change, value)
# 	return value
