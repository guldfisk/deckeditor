from abc import ABCMeta, abstractmethod

from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import QObject


class Action(QAction, metaclass=ABCMeta):

	def __init__(self, description: str, parent: QObject):
		super().__init__(description, parent)
		self.triggered.connect(self._perform)

	@abstractmethod
	def _perform(self):
		pass


class LoadDeck(Action):

	def __init__(self, parent: QObject):
		super().__init__(
			'Load Deck',
			parent,
		)

	def _perform(self):
		pass
