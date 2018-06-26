
import typing as t

from threading import Lock, Condition, Thread

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from promise import Promise

from PyQt5 import QtCore, QtGui

from mtgorp.db.database import CardDatabase
from mtgorp.db.load import Loader, DBLoadException
from mtgorp.managejson.update import check_and_update, update

from deckeditor.notifications.notifyable import Notifyable


T = t.TypeVar('T')


class TypedPromise(Promise, t.Generic[T]):

	def get(self, timeout=None) -> T:
		return super().get(timeout)


class Awaitable(Condition):

	def __init__(self):
		super().__init__()
		self._unlocked = False

	def notify_all(self) -> None:
		self._unlocked = True
		super().notify_all()

	def wait(self, timeout: t.Optional[float] = ...) -> bool:
		if not self._unlocked:
			return super().wait()

		return False


class DBLoader(object):

	# signal = QtCore.pyqtSignal(CardDatabase)

	# def __init__(self, notifyable: Notifyable):
	# 	self._notifyable = notifyable
	#
	# 	self._db = None #type: t.Optional[CardDatabase]
	#
	# 	self._condition = None #type: t.Optional[Condition]
	#
	#

	# @property
	# def notifyable(self) -> Notifyable:
	# 	return self._notifyable

	# def __init__(self):
	# 	super().__init__()
	# 	self._db = None #type: t.Optional[CardDatabase]
	#
	# 	# self._executor = ThreadPoolExecutor(1)

	db = None #type: t.Optional[CardDatabase]

	# @property
	# def db(self) -> CardDatabase:
	# 	return self._db

	@classmethod
	def init(cls) -> None:
		try:
			cls.db = Loader.load()
		except DBLoadException:
			# notifyable.notify('Building database...')
			update()
			cls.db = Loader.load()
			# notifyable.notify('Database build successfully')

	# def init(self, notifyable: Notifyable):
	# 	self._executor.submit(
	# 		self._init,
	# 		notifyable,
	# 	)

	# def _load(self) -> CardDatabase:
	# 	print('load db')
	# 	if self._condition is None:
	# 		self._condition = Awaitable()
	#
	# 		try:
	# 			self._db = Loader.load()
	# 		except DBLoadException:
	# 			self.notifyable.notify('Building database...')
	# 			update()
	# 			self._db = Loader.load()
	# 			self.notifyable.notify('Database build successfully')
	#
	# 		with self._condition:
	# 			print('notify lets go')
	# 			self._condition.notify_all()
	#
	# 	else:
	# 		with self._condition:
	# 			print('waiting...')
	# 			self._condition.wait()
	# 			print('done waiting')
	#
	# 	print('loaded db')
	# 	return self._db

	# def db(self) -> TypedPromise[CardDatabase]:
	# 	if self._db is None:
	# 		print('lmao')
	# 		# return TypedPromise(lambda resolve, reject: resolve(self._load()))
	# 		return TypedPromise.resolve(
	# 			self._executor.submit(self._load)
	# 		)
	#
	# 	else:
	# 		return TypedPromise.resolve(self._db)
