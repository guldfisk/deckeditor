import typing as t

from abc import ABCMeta, abstractmethod

from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtCore import QPointF

from deckeditor.cardcontainers.physicalcard import PhysicalCard
from deckeditor.undo.command import UndoCommand


class AttachmentChange(UndoCommand):
	pass


class AlignDetach(AttachmentChange):

	def expecting(self) -> t.Tuple[t.Type['AlignAttach'], t.Type['AlignRemove']]:
		return AlignAttach, AlignRemove


class AlignAttach(AttachmentChange):

	def merge(self, command: 'UndoCommand') -> bool:
		return isinstance(command, AlignRemove)


class AlignRemove(AttachmentChange):
	pass


class Aligner(object, metaclass=ABCMeta):

	def __init__(self, scene: QGraphicsScene):
		self._scene = scene

	@property
	def scene(self) -> QGraphicsScene:
		return self._scene

	@abstractmethod
	def attach_cards(self, cards: t.Iterable[PhysicalCard], position: QPointF) -> AlignAttach:
		pass

	@abstractmethod
	def detach_cards(self, cards: t.Iterable[PhysicalCard]) -> AlignDetach:
		pass

	@abstractmethod
	def remove_cards(self, cards: t.Iterable[PhysicalCard]) -> AlignRemove:
		pass