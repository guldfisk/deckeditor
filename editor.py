import os
import re
import sys

import xml.etree.ElementTree as ET
from PIL import ImageQt
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QMainWindow, QAction, QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap

from mtgorp.db.load import Loader as MtgLoader
from mtgorp.db.load import CardDatabase
from mtgorp.models.persistent import printing as _printing

from mtgimg.load import Loader as ImageLoader


class Globals(object):
	db = None #type: CardDatabase
	@classmethod
	def init(cls):
		cls.db = MtgLoader.load()

class Card(QGraphicsPixmapItem):
	def __init__(self, printing: _printing.Printing):
		super().__init__()
		self._printing = printing
		self.setPixmap(
			QPixmap.fromImage(
				ImageQt.ImageQt(
					ImageLoader.get_image(
						printing,
						callback=self._set_image,
						async=False,
					)
				)
			)
		)
	def _set_image(self, image_request, result):
		self.setPixmap(
			QPixmap.fromImage(
				ImageQt.ImageQt(
					result
				)
			)
		)

class CardContainer(QGraphicsView):
	def __init__(self):
		self._graphic_scene = QGraphicsScene()
		super().__init__(self._graphic_scene)
		printing = Globals.db.cardboards['Bloodghast'].from_expansion('ZEN')
		self._graphic_scene.addItem(
			Card(printing)
		)
		self._graphic_scene.addText(printing.cardboard.name)

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

		self.card_container = CardContainer()

		box.addWidget(self.card_container)

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
		
		self.setGeometry(300, 300, 300, 200)

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
	Globals.init()
	app=QtWidgets.QApplication(sys.argv)
	w=MainWindow()
	w.show()
	sys.exit(app.exec_())
	
if __name__=='__main__':
	run()