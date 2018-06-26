import sys
import time
import random
import os

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QMainWindow, QAction

from mtgorp.db.database import CardDatabase

from deckeditor.cardcontainers.cardwidget import CardWindow
from deckeditor.cardadd.cardadder import CardAdder
from deckeditor.undo.command import UndoStack
from deckeditor.cardcontainers.cardcontainer import AddPrintings
from deckeditor.cardcontainers.physicalcard import PhysicalCard
from deckeditor import paths

from deckeditor.notifications.frame import NotificationFrame
from deckeditor.notifications.notifyable import Notifyable

from deckeditor.dbload.load import DBLoader


random.seed()


class MainView(QWidget):

	def __init__(self, undo_stack: UndoStack, parent=None):
		super(MainView, self).__init__(parent)

		self._undo_stack = undo_stack

		# self.cardWidgets = {
		# 	'main': multiCardWidget.MultiCardWidget(self, imageloader=self.imageloader),
		# 	'side': multiCardWidget.MultiCardWidget(self, imageloader=self.imageloader),
		# 	'pool': multiCardWidget.MultiCardWidget(self, imageloader=self.imageloader)
		# }
		#
		self._card_adder = CardAdder()

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

		self._card_window = CardWindow(self._undo_stack)

		box.addWidget(
			CardWindow(self._undo_stack)
		)
		box.addWidget(
			self._card_window
		)
		box.addWidget(self._card_adder)

		self._card_adder.hide()

		self.setLayout(
			box
		)

	@property
	def card_window(self) -> CardWindow:
		return self._card_window


class MainWindow(QMainWindow, Notifyable):

	def __init__(self, parent=None):
		super(MainWindow,self).__init__(parent)

		self._undo_stack = UndoStack()

		self._db_loader = DBLoader()

		self._notification_frame = NotificationFrame(self)

		self.showMaximized()

		self.main_view = MainView(self._undo_stack, self)

		self.setCentralWidget(self.main_view)

		self.setWindowTitle('Deckeditor')

		menu_bar = self.menuBar()

		all_menus = {
			menu_bar.addMenu('Edit'): (
				('Undo', 'Ctrl+Z', self._undo_stack.undo),
				('Redo', 'Ctrl+Shift+Z', self._undo_stack.redo),
				# ('Scroll Up', 'W', lambda : self.main_view.card_window.scroll(-5, 0)),
				# ('Scroll Right', 'D', lambda : self.main_view.card_window.scroll(0, 5)),
				# ('Scroll Down', 'S', lambda : self.main_view.card_window.scroll(5, 0)),
				# ('Scroll Left', 'A', lambda : self.main_view.card_window.scroll(0, -5)),
			),
			menu_bar.addMenu('File'): (
				('Exit', 'Ctrl+Q', QtWidgets.qApp.quit),
				('Load Deck', 'Ctrl+O', self.load),
				('Load Pool', 'Ctrl+P', self.load_pool),
				('Save deck', 'Ctrl+S', self.save),
				('Save pool', 'Ctrl+l', self.save_pool)
			),
			menu_bar.addMenu('Generate'): (
				('Sealed pool', 'Ctrl+G', self.generate_pool),
				('Cube Pools', 'Ctrl+C', self.generate_cube_pools)
			),
			menu_bar.addMenu('Add'): (
				('Add cards', 'Ctrl+F', self.add_card),
			),
			menu_bar.addMenu('Test'): (
				('Test', 'Ctrl+T', self._test),
			),
		}

		for menu in all_menus:
			for subMenu in all_menus[menu]:
				action = QAction(subMenu[0], self)
				action.setShortcut(subMenu[1])
				action.triggered.connect(subMenu[2])
				menu.addAction(action)

		self._printings = None

	def notify(self, message: str) -> None:
		self._notification_frame.notify(message)

	def _test(self):
		self.notify('lol xd kasdhfkashdfklasdhfkashdfk'*2)

	def resizeEvent(self, QResizeEvent):
		if hasattr(self, '_notification_frame'):
			self._notification_frame.stack_notifications()

	def _add_card(self, db: CardDatabase):
		print('add card')
		if self._printings is None:
			self._printings = list(db.printings.values())

		sampled = random.sample(self._printings, 20)

		self._undo_stack.push(
			AddPrintings(
				self.main_view.card_window.card_container.scene(),
				sampled,
				QtCore.QPointF(0, 0),
			)
		)

	def add_card(self):
		# self._add_card(self._db_loader.db().get())
		# self._db_loader.db().then(self._add_card)
		self._add_card(DBLoader.db)

	def save_pool(self):
		pass

	def load_pool(self):
		pass

	def generate_cube_pools(self):
		pass

	def load(self):
		pass

	def save(self):
		pass

	def generate_pool(self):
		pass


def run():

	app = QtWidgets.QApplication(sys.argv)

	splash_image = QtGui.QPixmap(os.path.join(paths.RESOURCE_PATH, 'splash.png'))

	splash = QtWidgets.QSplashScreen(splash_image)

	splash.show()

	time.sleep(0.2)
	app.processEvents()

	PhysicalCard.init()

	DBLoader.init()

	with open(os.path.join(paths.RESOURCE_PATH, 'style.qss'), 'r') as f:
		app.setStyleSheet(f.read())

	QtWidgets.QApplication.setOrganizationName('EmbargoSoft')
	QtWidgets.QApplication.setOrganizationDomain('ce.lost-world.dk')
	QtWidgets.QApplication.setApplicationName('Embargo Edit')


	w = MainWindow()

	w.show()

	splash.finish(w)

	sys.exit(app.exec_())



if __name__=='__main__':
	run()