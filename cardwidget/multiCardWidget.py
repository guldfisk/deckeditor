import copy
import math as m
import pickle
import numpy as np
import pygame as pg
from PyQt5 import QtWidgets, QtGui, QtCore
from cardwidget import embedableSurface
from constructs import mtgObjects
from resourceload.cardload import CardLoader
from resourceload.imageload import ImageLoader

pg.font.init()

class DEImageLoader(ImageLoader):
	image_name_font = pg.font.Font(None, 18)
	def _load_image(self, path, name, card):
		with open(path, 'rb') as f:
			full = pg.image.load(f)
			half = pg.transform.scale(full, (int(full.get_width()/2), int(full.get_height()/2)))
			color = card.getImageColor()
			name_text = self.image_name_font.render(
				card.get('name', 'Default'),
				1,
				color,
				tuple(max(channel-155, 0) for channel in color)
			)
			if half.get_width()<name_text.get_width():
				name_text = pg.transform.scale(name_text, (half.get_width(), name_text.get_height()))
			half.blit(name_text, name_text.get_rect())
			self.images[name+'_full'] = full
			self.images[name] = half

class DECard(object):
	def __init__(self, session, card):
		self.session = session
		if not isinstance(card, mtgObjects.Card):
			internal_card = mtgObjects.Card(card)
		else:
			internal_card = card
		if not 'set' in internal_card and 'printings' in internal_card:
			self.card = mtgObjects.Card.getThisFromSet(internal_card, internal_card['printings'][0])
		else:
			self.card = internal_card
		self.rekt = self.session.imageLoader.get_image(self).get_rect()
	def __getattr__(self, attr):
		return self.card.__getattribute__(attr)
	def __getitem__(self, key):
		return self.card.__getitem__(key)
	def __setitem__(self, key, value):
		self.card.__setitem__(key, value)
	def __iter__(self):
		return self.card.__iter__()
	def get(self, key, default):
		return self.card.get(key, default)
	def draw(self, surface):
		surface.blit(self.session.imageLoader.get_image(self), self.rekt)
		if self in self.session.selected: pg.draw.rect(surface, (255, 0, 0), self.rekt, 3)
	def move(self, x, y):
		self.session.upToDate = False
		self.rekt.move_ip(x, y)
		self.rekt.clamp_ip(pg.Rect((0, 0), self.session.getSize()))
	def move_to(self, x, y):
		self.session.upToDate = False
		self.rekt.x, self.rekt.y = x, y
		self.rekt.clamp_ip(pg.Rect((0, 0), self.session.getSize()))
	def change_to_set(self):
		key, ok = QtWidgets.QInputDialog.getItem(
			self.session,
			'Select set',
			'Select set',
			CardLoader.get_cards().get(self['name'], mtgObjects.Card()).get('printings', [])
		)
		if not ok or not key:
			return
		self.session.selected.add(self)
		for card in self.session.selected:
			if card['name']==self['name']: card['set'] = key
		self.session.redraw()
	def right_clicked(self, menu, mapping):
		if hasattr(self.card, 'rightClicked'):
			self.card.rightClicked(menu, mapping)
		mapping[menu.addAction('Change to set')] = FuncWithArg(self.change_to_set)

class Stack(object):
	def __init__(self, session, pos = (0, 0), dim = (100, 100)):
		self.session = session
		self.cards = []
		self.rekt = pg.Rect(pos, dim)
	def move(self, x, y):
		self.rekt.move_ip(x, y)
		self.align_all()
	def move_to(self, x, y):
		self.rekt.x, self.rekt.y = x, y
		self.align_all()
	def resize(self, x, y, w, h):
		self.rekt.w, self.rekt.h = w, h
		self.move_to(x, y)
	def align_all(self):
		for i in range(len(self.cards)):
			self.cards[i].move_to(
				self.rekt[0],
				self.rekt[1] + i * max(self.rekt.h - self.cards[i].rekt.h, 0) / len(self.cards)
			)
	def put(self, card):
		self.cards.append(card)
		self.align_all()
	def take(self, card):
		try:
			self.cards.remove(card)
		except ValueError:
			return
		self.align_all()
	def pick_up(self, card):
		if card in self.cards:
			self.take(card)
			return True
	def drop(self, card, pos):
		if self.rekt.collidepoint(pos):
			self.put(card)
			return True

class UIElement(object):
	def __init__(self, session):
		self.session = session
		self.session.uielements.append(self)
	def draw(self, surface):
		raise NotImplemented

class SelectionBox(UIElement):
	def __init__(self, session, anchor = (0, 0)):
		super(SelectionBox, self).__init__(session)
		self.anchor = np.array(anchor)
		self.corner = np.array(anchor)
		self.pos = [0, 0]
		self.dim = [0, 0]
		self.s = None
		self.new_surface()
	def new_surface(self):
		for i in range(2):
			if self.anchor[i]<self.corner[i]:
				self.pos[i] = self.anchor[i]
				self.dim[i] = self.corner[i]-self.anchor[i]
			else:
				self.pos[i] = self.corner[i]
				self.dim[i] = self.anchor[i]-self.corner[i]
		self.s = pg.Surface(self.dim)
		self.s.set_alpha(128)
	def resize_to(self, pos):
		self.corner = np.array(pos)
		self.new_surface()
		self.update_collision()
	def resize(self, rel):
		self.corner += rel
		self.new_surface()
		self.update_collision()
	def draw(self, surface):
		surface.blit(self.s, self.pos)
	def update_collision(self):
		col_rec = pg.Rect(self.pos, self.dim)
		self.session.updateSelected(*tuple(card for card in self.session.cards if card.rekt.colliderect(col_rec)))
	def end(self):
		self.update_collision()
		self.session.uielements.remove(self)

class FuncWithArg(object):
	def __init__(self, f, *args, **kwargs):
		self.f = f
		self.args = args
		self.kwargs = kwargs
	def run(self):
		self.f(*self.args, **self.kwargs)

class MultiCardWidget(embedableSurface.EmbeddedSurface):
	font = pg.font.Font(None, 30)
	def __init__(self, parent, **kwargs):
		super(MultiCardWidget, self).__init__()
		self.parent = parent
		self.imageLoader = kwargs.get('imageloader', DEImageLoader())
		self.cards = []
		self.stacks = []
		self.floatingStack = Stack(self)
		self.selectionbox = None
		self.selected = set()
		self.uielements = []
		self.lastGridDimensions = (0, 0)
		self.makeStacks()
		self.setAcceptDrops(True)
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.context_menu)
		self.setMouseTracking(True)
	def pick_up_cards(self, *cards, pos=(0, 0)):
		self.floatingStack = Stack(self, pos=pos)
		for card in cards: self.pick_up_card(card)
	def pick_up_card(self, card):
		self.moveCardsToFront(card)
		self.floatingStack.put(card)
		for r in self.stacks:
			for c in r:
				if c.pick_up(card): return
	def drop_cards(self, pos, *cards):
		for card in cards: self.drop_card(card, pos)
	def drop_card(self, card, pos):
		if card in self.floatingStack.cards: self.floatingStack.cards.remove(card)
		for r in self.stacks:
			for c in r:
				if c.drop(card, pos): return
		card.move_to(*pos)
	def reposition_card(self, card, pos):
		self.pick_up_card(card)
		self.drop_card(card, pos)
	def sort_cards(self, f=mtgObjects.Card.cmcSortValue, row=True, reverse=False):
		if not self.cards: return
		if self.selected: cards = self.selected
		else: cards = self.cards
		sorted_cards = sorted(
			sorted(
				copy.copy(cards),
				key= lambda o: o['name']),
			key = lambda o: f(o),
			reverse=reverse
		)
		value = f(sorted_cards[0])
		stack = 0
		for card in sorted_cards:
			if not f(card)==value:
				stack += 1
				if row and stack>len(self.stacks)-1: stack = len(self.stacks)-1
				elif not row and stack>len(self.stacks[0])-1: stack = len(self.stacks[0])-1
				value = f(card)
			if row: self.reposition_card(card, (self.stacks[stack][0].rekt.x, card.rekt.y))
			else: self.reposition_card(card, (card.rekt.x, self.stacks[0][stack].rekt.y))
		self.redraw()
	def context_menu(self, pos):
		menu = QtWidgets.QMenu()
		row_sort = QtWidgets.QMenu('Sort rows')
		column_sort = QtWidgets.QMenu('Sort columns')
		mapping = {
			row_sort.addAction('CMC'): FuncWithArg(self.sort_cards, mtgObjects.Card.cmcSortValue),
			row_sort.addAction('Color'): FuncWithArg(self.sort_cards, mtgObjects.Card.colorSortValue),
			row_sort.addAction('Rarity'): FuncWithArg(self.sort_cards, mtgObjects.Card.raritySortValue),
			row_sort.addAction('Type'): FuncWithArg(self.sort_cards, mtgObjects.Card.typeSortValue),
			row_sort.addAction('Is creature'): FuncWithArg(self.sort_cards, mtgObjects.Card.isCreature, True, True),
			row_sort.addAction('Is permanent'): FuncWithArg(self.sort_cards, mtgObjects.Card.isPermanent),
			column_sort.addAction('Is creature'): FuncWithArg(self.sort_cards, mtgObjects.Card.isCreature, False, True),
			column_sort.addAction('Is permanent'): FuncWithArg(self.sort_cards, mtgObjects.Card.isPermanent, False),
			column_sort.addAction('CMC'): FuncWithArg(self.sort_cards, mtgObjects.Card.cmcSortValue, False),
			column_sort.addAction('Color'): FuncWithArg(self.sort_cards, mtgObjects.Card.colorSortValue, False),
			column_sort.addAction('Rarity'): FuncWithArg(self.sort_cards, mtgObjects.Card.raritySortValue, False),
			column_sort.addAction('Type'): FuncWithArg(self.sort_cards, mtgObjects.Card.typeSortValue, False)
		}
		card = self.getTopCollision((pos.x(), pos.y()))
		if card: card.rightClicked(menu, mapping)
		menu.addMenu(row_sort)
		menu.addMenu(column_sort)
		action = menu.exec_(self.mapToGlobal(pos))
		if action: mapping[action].run()
	def remove_floating_cards(self):
		self.removeCards(*self.floatingStack.cards)
		self.floatingStack.cards[:] = []
	def grabFloatingCards(self):
		drag = QtGui.QDrag(self)
		mime = QtCore.QMimeData()
		stream = QtCore.QByteArray()
		stream.append(pickle.dumps(tuple(dict(card.card) for card in self.floatingStack.cards)))
		mime.setData('cards', stream)
		drag.setMimeData(mime)
		drag.exec_()
	def keyPressEvent(self, event):
		key = event.key()
		if key==QtCore.Qt.Key_Delete: self.removeCards(*self.selected)
	def mousePressEvent(self, event):
		if not event.buttons()==QtCore.Qt.LeftButton: return
		self.setFocus(QtCore.Qt.TabFocusReason)
		pos = (event.pos().x(), event.pos().y())
		card = self.getTopCollision(pos)
		if card:
			self.parent.cardadder.setStagingCard(card, False)
			if not card in self.selected: self.updateSelected(card)
			self.pick_up_cards(*self.selected, pos=pos)
		else: self.selectionbox = SelectionBox(self, pos)
		self.redraw()
	def mouseMoveEvent(self, event):
		pos = (event.pos().x(), event.pos().y())
		card = self.getTopCollision(pos)
		if card: self.parent.hover.setCard(card)
		if not event.buttons()==QtCore.Qt.LeftButton: return
		if self.selectionbox:
			self.selectionbox.resize_to(pos)
		elif self.selected:
			if pos[0]<0 or pos[1]<0 or self.getSize()[0]<pos[0] or self.getSize()[1]<pos[1]:
				self.grabFloatingCards()
			else:
				for card in self.selected: card.move_to(*pos)
		self.redraw()
	def mouseReleaseEvent(self, event):
		pos = (event.pos().x(), event.pos().y())
		if self.selectionbox:
			self.selectionbox.end()
			self.selectionbox = None
		if self.floatingStack.cards:
			self.drop_cards(pos, *self.floatingStack.cards)
		self.redraw()
	def dragEnterEvent(self, event):
		if event.mimeData().data('cards'): event.accept()
	def dropEvent(self, event):
		if event.source(): event.source().remove_floating_cards()
		pos = (event.pos().x(), event.pos().y())
		cards = pickle.loads(event.mimeData().data('cards'))
		self.addCards(*pickle.loads(event.mimeData().data('cards')), pos=pos)
		self.redraw()
	def getSize(self):
		return (self.size().width(), self.size().height())
	def makeStacks(self, columns=5, rows=2):
		x, y = self.getSize()
		if (x, y)==self.lastGridDimensions: return
		self.lastGridDimensions = (x, y)
		self.stacks[:] = []
		w, h = self.imageLoader.get_default().get_rect().w, self.imageLoader.get_default().get_rect().h
		rows, columns = max(m.floor(x/w), 1), min(max(m.floor(y/h), 1), 2)
		for r in range(rows):
			self.stacks.append([])
			for c in range(columns):
				stack = Stack(self)
				stack.resize(int(x/rows*r), int(y/columns*c), int(x/rows), int(y/columns))
				self.stacks[r].append(stack)
		for card in self.cards: self.drop_card(card, (card.rekt.centerx, card.rekt.centery))
	def moveCardsToFront(self, *cards):
		for card in cards:
			if card in self.cards:
				self.cards.remove(card)
				self.cards.append(card)
	def updateSelected(self, *cards):
		self.selected.clear()
		self.selected.update(cards)
	def getTopCollision(self, point):
		for i in range(len(self.cards)-1, -1, -1):
			if self.cards[i].rekt.collidepoint(point): return self.cards[i]
		return None
	def get_surface(self):
		self.makeStacks()
		sz = (self.size().width(), self.size().height())
		surface = pg.Surface(sz)
		surface.fill((128, 128, 128))
		for card in self.cards: card.draw(surface)
		for uie in self.uielements: uie.draw(surface)
		amount_card_text_surface = self.font.render(
			str(len(self.cards))+'('+str(len(self.selected))+') cards',
			1,
			(255, 255, 255),
			(0, 0, 0)
		)
		rekt = amount_card_text_surface.get_rect()
		rekt.move_ip(0, sz[1]-rekt.h)
		surface.blit(amount_card_text_surface, rekt)
		return surface
	def addCards(self, *cards, pos = (0, 0)):
		cards = list(DECard(self, card) for card in cards)
		self.cards.extend(cards)
		self.drop_cards(pos, *cards)
		self.redraw()
	def removeCards(self, *cards):
		self.pick_up_cards(*cards)
		for card in cards:
			try: self.cards.remove(card)
			except ValueError: pass
			try: self.selected.remove(card)
			except KeyError: pass
		self.redraw()
	def clear(self):
		self.pick_up_cards(*self.cards)
		self.remove_floating_cards()
		self.selected = set()
