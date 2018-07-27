import typing as t

from abc import abstractmethod

from PyQt5 import QtCore


from mtgorp.models.persistent.printing import Printing
from mtgorp.utilities.containers import Multiset



class CardCollection(QtCore.QObject):

	def __init__(self):
		super().__init__()

		self._maindeck = Multiset() #type: Multiset[Printing]
		self._sideboard = Multiset() #type: Multiset[Printing]

