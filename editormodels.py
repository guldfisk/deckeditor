from models import mtgObjects

class PhysicalCard(mtgObjects.Card):
	color_colors = {
		'White': (230, 230, 150),
		'Blue': (0, 0, 200),
		'Black': (220, 220, 220),
		'Red': (255, 0, 0),
		'Green': (0, 200, 0),
		'Gold': (230, 230, 0),
		'Colorless': (255, 200, 150)
	}
	def get_image_color(self):
		if not 'colors' in self or not self['colors']:
			return PhysicalCard.color_colors['Colorless']
		elif len(self['colors'])>1:
			return PhysicalCard.color_colors['Gold']
		return PhysicalCard.color_colors.get(self['colors'][0], (100, 100, 100))
	color_values = {
			'White': 0,
			'Blue': 1,
			'Black': 2,
			'Red': 3,
			'Green': 4
		}
	def colorSortValue(self):
		if not 'colors' in self or not self['colors']: return 6
		elif len(self['colors'])>1: return 5
		return PhysicalCard.color_values.get(self['colors'][0], 6)
	raritySortValueDict = {
		'Common': 0,
		'Uncommon': 1,
		'Rare': 2,
		'Mythic Rare': 3
	}
	def raritySortValue(self):
		return PhysicalCard.raritySortValueDict.get(self.get('rarity', 'norarity'), 4)
	def isPermanent(self):
		return mtgObjects.NamedCards.nonpermanentCard.match(self)
	def isCreature(self):
		return mtgObjects.NamedCards.creatureCard.match(self)
	def cmcSortValue(self):
		return self.get('cmc', 0)
	def typeSortValue(self):
		if mtgObjects.NamedCards.landCard.match(self): return 0
		elif mtgObjects.NamedCards.creatureCard.match(self): return 1
		elif mtgObjects.NamedCards.instantCard.match(self): return 2
		elif mtgObjects.NamedCards.sorceryCard.match(self): return 3
		elif mtgObjects.NamedCards.artifactCard.match(self): return 4
		elif mtgObjects.NamedCards.enchantmentCard.match(self): return 5
		elif mtgObjects.NamedCards.planeswalkerCard.match(self): return 6