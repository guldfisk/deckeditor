import typing as t

from PyQt5 import QtCore

from cardcontainers.card import Card

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