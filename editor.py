import os
import re
import sys
import threading
import time
import itertools
import pickle

import typing as t
import xml.etree.ElementTree as ET

from promise import Promise
from PIL import ImageQt
from PyQt5 import QtWidgets, QtCore, QtGui, Qt
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QMainWindow, QAction, QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap, QTransform

from mtgorp.db.load import Loader as MtgLoader
from mtgorp.db.load import CardDatabase
from mtgorp.models.persistent import printing as _printing

from orp.relationships import One, Many, OneDescriptor

from mtgimg import load as imageload


class Globals(object):
	db = None #type: CardDatabase
	@classmethod
	def init(cls):
		cls.db = MtgLoader.load()

class ImageLoader(imageload.Loader):
	@classmethod
	def get_pixmap(
		cls,
		printing: _printing.Printing = None,
		back: bool = False,
		crop: bool = False,
		image_request: imageload.ImageRequest = None
	) -> Promise:
		return cls.get_image(
			printing,
			back,
			crop,
			image_request,
		).then(
			lambda image: QPixmap.fromImage(
				ImageQt.ImageQt(
					image
				)
			)
		)
	@classmethod
	def get_default_pixmap(cls):
		print('get default pixmap')
		return cls.get_default_image().then(
			lambda image: QPixmap.fromImage(ImageQt.ImageQt(image))
		)

class TestThread(threading.Thread):
	def __init__(self, f, *args, **kwargs):
		super().__init__()
		self.f = f
		self.args = args
		self.kwargs = kwargs
	def run(self):
		time.sleep(3)
		self.f(*self.args, **self.kwargs)

class Card(QtWidgets.QGraphicsObject):
	signal = QtCore.pyqtSignal(object)
	# noinspection PyCallByClass
	def __init__(self, printing: _printing.Printing):
		super().__init__()
		self._selection_highlite_pen = QtGui.QPen(QtGui.QColor(255, 0, 0), 2)
		self._printing = printing
		self._pixmap = None #type: QtGui.QPixmap
		self._bounding_rect = QtCore.QRectF()
		pixmap_promise = ImageLoader.get_pixmap(self._printing)
		if pixmap_promise.is_fulfilled:
			self.setPixmap(pixmap_promise.get())
			print('bounding rect', self.boundingRect().x(), self.boundingRect().y(), self.boundingRect().width(), self.boundingRect().height())
		else:
			print('pic not on local')
			print(isinstance(self, QGraphicsPixmapItem))
			print(dir(self))
			self.setPixmap(ImageLoader.get_default_pixmap().get())

			self.signal.connect(self._set_image)
			print('connected')
		pixmap_promise.then(self.signal.emit)
		self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
		self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
		self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
		# self.move_to_top()
		self._card_stacker = None #type: CardStacker
	@property
	def card_stacker(self):
		return self._card_stacker
	@card_stacker.setter
	def card_stacker(self, card_stacker: 'CardStacker'):
		self._card_stacker = card_stacker
	def pixmap(self):
		return self._pixmap
	def setPixmap(self, pixmap: 'QtGui.QPixmap'):
		self._pixmap = pixmap
		self._bounding_rect = QtCore.QRectF(0, 0, pixmap.size().width(), pixmap.size().height())
	def paint(self, painter: QtGui.QPainter, options, widget=None):
		painter.drawPixmap(QtCore.QPointF(0, 0), self._pixmap)
		if self.isSelected():
			painter.setPen(self._selection_highlite_pen)
			painter.drawRect(self.boundingRect())
	def boundingRect(self):
		return self._bounding_rect
	def _set_image(self, pixmap: QPixmap):
		print('set image')
		# pixmap = ImageLoader.get_default_pixmap().get()
		print('setting real pixmap', pixmap, type(pixmap), pixmap.size())
		self.setPixmap(pixmap)
		print('done, updating')
		self.update()
		try:
			print(
				'update done',
				self.pixmap().size(),
				(self.pos().x(), self.pos().y()), (self.scenePos().x(), self.scenePos().y()),
				self.boundingRect(),
			)
		except Exception as e:
			print('rip', e)
	def align(self, pos: QtCore.QPointF):
		self.scene().get_card_stacker(pos.x(), pos.y()).add_card(self)
	def mouseDoubleClickEvent(self, *args, **kwargs):
		print('double clicked')
		ImageLoader.get_pixmap(Globals.db.cardboards['Lightning Bolt'].from_expansion('LEA')).then(self._set_image)
	def mouseReleaseEvent(self, event):
		super().mouseReleaseEvent(event)
		print('mouse release event', self, event.pos(), self.scene())
		print(self.scene().get_card_stacker(event.scenePos().x(), event.scenePos().y()))
		for item in self.scene().selectedItems():
			if isinstance(item, Card):
				item.align(event.scenePos())
	def mousePressEvent(self, event):
		super().mousePressEvent(event)
		print('mouse pressed', self, event, self.scene().selectedItems())
		for item in self.scene().selectedItems():
			print(item.card_stacker)
			if isinstance(item, Card) and item.card_stacker is not None:
				print('lets go', item.card_stacker.cards)
				print(item)
				item.card_stacker.remove_card(item)
				print('card removed')
	def itemChange(self, change, value):
		# super().itemChange(change, value)
		# if change==QtWidgets.QGraphicsItem.ItemSelectedChange and value:
		# 	self.move_to_top()
		if change==QtWidgets.QGraphicsItem.ItemSceneChange:
			if self._card_stacker is not None:
				self._card_stacker.remove_card(self)
		# if change==QtWidgets.QGraphicsItem.ItemPositionHasChanged:
		# 	print('position change', value)
		# return QtWidgets.QGraphicsItem.itemChange(change, value)
		return value

class CardStacker(object):
	def __init__(self, position: t.Tuple[float, float], spacing = 100):
		self._position = position
		self._spacing = spacing
		self.cards = [] #type: t.List[Card]
		self._z = 0
	def stack(self):
		for i in range(len(self.cards)):
			self.cards[i].setPos(
				QtCore.QPoint(
					self._position[0],
					self._position[1] + i*self._spacing
				)
			)
			self.cards[i].setZValue(self._z+i)
	def _remove_card(self, card: Card):
		try:
			self.cards.remove(card)
			card.card_stacker = None
		except KeyError:
			pass
	def _add_card(self, card: Card):
		if card.card_stacker is not None:
			card.card_stacker.remove_card(card)
		card.card_stacker = self
		self.cards.append(card)
	def remove_card(self, card: Card):
		self._remove_card(card)
		self.stack()
	def add_card(self, card: Card):
		self._add_card(card)
		self.stack()
	def remove_cards(self, cards: t.Iterable[Card]):
		for card in cards:
			self._remove_card(card)
		self.stack()
	def add_cards(self, cards: t.Iterable[Card]):
		for card in cards:
			self._add_card(card)
		self.stack()

class CardScene(QGraphicsScene):
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

class CardContainer(QGraphicsView):
	def __init__(self):
		self._graphic_scene = CardScene()
		super().__init__(self._graphic_scene)
		self.setDragMode(QGraphicsView.RubberBandDrag)
		self.setAcceptDrops(True)

		printing = Globals.db.cardboards['Bloodghast'].from_expansion('ZEN')
		another_printing = Globals.db.cardboards['Dive Down'].from_expansion('XLN')
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
		if drop_event.source()==self:
			for item in self.scene().selectedItems():
				item.align(self.mapToScene(drop_event.pos()))
		else:
			for item in drop_event.source().scene().selectedItems():
				self.scene().addItem(item)
				item.align(self.mapToScene(drop_event.pos()))
	def mouseMoveEvent(self, mouse_event: QtGui.QMouseEvent):
		super().mouseMoveEvent(mouse_event)
		if not QtCore.QRectF(0, 0, self.size().width(), self.size().height()).contains(mouse_event.pos()):
			# mouse_event.accept()
			drag = QtGui.QDrag(self)
			# mime = QtCore.QMimeData()
			# stream = QtCore.QByteArray()
			# stream.append(pickle.dumps((1, 2, 3)))
			# mime.setData('cards', stream)
			# drag.setMimeData(mime)
			# print('drag', drag, mime)
			drag.exec_()
		# 	return
		# mouse_event.ignore()
	# def mousePressEvent(self, mouse_event: QtGui.QMouseEvent):
	# 	super().mousePressEvent(mouse_event)
	# 	print(
	# 		'mouse press event',
	# 		self.itemAt(mouse_event.pos()),
	# 		mouse_event.pos(),
	# 	)
	# def mouseMoveEvent(self, mouse_event: QtGui.QMouseEvent):
	# 	super().mouseMoveEvent(mouse_event)
	# 	# print('mouse move event', mouse_event, self)

class ScaleSlider(QtWidgets.QSlider):
	def __init__(self, *__args):
		super().__init__(QtCore.Qt.Horizontal)
		self.setMinimum(1)
		self.setMaximum(100)
		self.setValue(100)

class CardWindow(QtWidgets.QWidget):
	def __init__(self):
		super().__init__()
		self.slider = ScaleSlider(Qt)
		self.card_container = CardContainer()
		self.slider.valueChanged.connect(
			lambda v: self.card_container.setTransform(QTransform().scale(v/100, v/100))
		)
		self.slider.setValue(50)
		box = QtWidgets.QVBoxLayout(self)
		box.addWidget(self.card_container)
		box.addWidget(self.slider)
		self.setLayout(box)

class MainView(QWidget):
	def __init__(self, parent=None):
		super(MainView, self).__init__(parent)

		# self.cardWidgets = {
		# 	'main': multiCardWidget.MultiCardWidget(self, imageloader=self.imageloader),
		# 	'side': multiCardWidget.MultiCardWidget(self, imageloader=self.imageloader),
		# 	'pool': multiCardWidget.MultiCardWidget(self, imageloader=self.imageloader)
		# }
		#
		box = QtWidgets.QHBoxLayout(self)
		#
		# botsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
		# botsplitter.addWidget(self.cardWidgets['main'])
		# botsplitter.addWidget(self.cardWidgets['side'])
		#
		# topsplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
		# topsplitter.addWidget(self.cardWidgets['pool'])
		# topsplitter.addWidget(botsplitter)
		#
		# vbox = QtWidgets.QVBoxLayout(self)
		#
		# vbox.addWidget(self.cardadder)
		# vbox.addWidget(self.hover)
		#
		# box.addWidget(topsplitter)
		# box.addLayout(vbox)

		# self.card_window = CardWindow()

		box.addWidget(
			CardWindow()
		)
		box.addWidget(
			CardWindow()
		)

		self.setLayout(
			box
		)

class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow,self).__init__(parent)

		# self.setWindowIcon(QtGui.QIcon(os.path.join(locate.path, 'handelsforbud.png')))

		self.mainview = MainView()

		self.setCentralWidget(self.mainview)

		self.setWindowTitle('Deckeditor')

		menubar = self.menuBar()

		allMenues = {
			menubar.addMenu('File'): (
				('Exit', 'Ctrl+Q', QtWidgets.qApp.quit),
				('Load Deck', 'Ctrl+O', self.load),
				('Load Pool', 'Ctrl+P', self.loadPool),
				('Save deck', 'Ctrl+S', self.save),
				('Save pool', 'Ctrl+l', self.savePool)
			),
			menubar.addMenu('Generate'): (
				('Sealed pool', 'Ctrl+G', self.generatePool),
				('Cube Pools', 'Ctrl+C', self.generateCubePools)
			),
			menubar.addMenu('Add'): (
				('Add cards', 'Ctrl+f', self.addCard),
			),
		}

		for menu in allMenues:
			for subMenu in allMenues[menu]:
				action = QAction(subMenu[0], self)
				action.setShortcut(subMenu[1])
				action.triggered.connect(subMenu[2])
				menu.addAction(action)

		# self.setGeometry(300, 300, 300, 200)
		self.showMaximized()
		# self.setFocus()
		# self.setWindowState()

	def addCard(self):
		pass
	def savePool(self):
		pass
	def loadPool(self):
		pass
	def generateCubePools(self):
		pass
	def load(self, asPool=False):
		pass
	def save(self, asPool=False):
		pass
	def generatePool(self):
		pass

def run():
	print('initing')
	Globals.init()
	print('init done')
	app=QtWidgets.QApplication(sys.argv)
	w=MainWindow()
	w.show()
	sys.exit(app.exec_())

def test():
	print('lego')
	app=QtWidgets.QApplication(sys.argv)
	print('okay')
	# pixmap_1 = ImageLoader.get_default_pixmap().get()
	pixmap_1 = imageload.Loader.get_default_image().get()
	print(pixmap_1)
	pixmap_2 = ImageLoader.get_default_pixmap().get()
	print(pixmap_2)
	app.quit()
	sys.exit(app.exec_())
	print('xd')
	sys.exit()

	# run()

if __name__=='__main__':
	run()