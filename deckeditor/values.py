from enum import Enum


class DeckZone(Enum):
	MAINDECK = 'Maindeck'
	SIDEBOARD = 'Sideboard'
	POOL = 'Pool'


class SortProperty(Enum):
	NAME = 'Name'
	CMC = 'Cmc'
	RARITY = 'Rarity'
	COLOR = 'Color'
	TYPE = 'Type'
	EXPANSION = 'Expansion'
	COLLECTOR_NUMBER = 'Collector Number'
