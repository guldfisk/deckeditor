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

from mtgimg import load as imageload

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
	QtWidgets.QApplication.setOrganizationName('EmbargoSoft')
	QtWidgets.QApplication.setOrganizationDomain('ce.lost-world.dk')
	QtWidgets.QApplication.setApplicationName('Embargo Edit')
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