import typing as t

from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QUndoCommand

from deckeditor.cardcontainers import Card, CardScene

from deckeditor.cardcontainers.alignment.aligner import AlignAttach, AlignDetach


class MoveCards(QUndoCommand):
	def __init__(
		self,
		cards: t.Tuple[Card, ...],
		origin_scene: CardScene,
		origin_position: QPointF,
		destination_scene: CardScene,
		destination_position: QPointF,
	):
		super().__init__()
		self._cards = cards
		self._origin_scene = origin_scene
		self._origin_position = origin_position
		self._destination_scene = destination_scene
		self._destination_position = destination_position

		self._aligner_attach = None #type: AlignAttach
		self._aligner_detach = None #type: AlignDetach

	def redo(self):
		if self._aligner_attach is None:
			self._aligner_detach = self._origin_scene.aligner.detach_cards(self._cards, self._origin_position)
			self._aligner_attach = self._destination_scene.aligner.attach_cards(self._cards, self._destination_position)

		self._aligner_detach.redo()
		self._aligner_attach.redo()

	def undo(self):
		self._aligner_attach.undo()
		self._aligner_detach.undo()