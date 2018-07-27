import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui

from mtgorp.models.persistent.printing import Printing

from deckeditor.cardcontainers.cardcontainer import CardContainer, ChangeAligner
from deckeditor.undo.command import UndoStack
from deckeditor.cardcontainers.alignment.stackinggrids.staticstackinggrid import StaticStackingGrid
from deckeditor.cardcontainers.alignment.grid import GridAligner
from deckeditor.context.context import Context
from deckeditor.values import DeckZone


class ScaleSlider(QtWidgets.QSlider):

	def __init__(self, *__args):
		super().__init__(QtCore.Qt.Horizontal)
		self.setMinimum(1)
		self.setMaximum(100)
		self.setValue(100)


class SelectedInfo(QtWidgets.QLabel):

	def set_amount_selected(self, selected: int = 0):
		self.setText(f'{selected} selected items')


class AlignSelector(QtWidgets.QComboBox):

	def __init__(self, parent=None):
		super().__init__(parent=parent)
		self.addItem('Stacking Grid')
		self.addItem('Grid')
		self.setCurrentIndex(0)


class DeckZoneWidget(QtWidgets.QWidget):
	content_changed = QtCore.pyqtSignal()

	def __init__(self, zone: DeckZone, undo_stack: UndoStack, parent = None):
		super().__init__(parent = parent)

		self._zone = zone
		self._undo_stack = undo_stack

		self._card_container = CardContainer(
			self._undo_stack,
			StaticStackingGrid,
		)
		self._zone_label = QtWidgets.QLabel(self)
		self._selected_info = SelectedInfo()
		self._aligner_selector = AlignSelector(self)

		self._zone_label.setText(self._zone.value)

		self._card_container.scene().selectionChanged.connect(self.selection_change)

		default_scale = Context.settings.value('default_card_view_scale', .2, float)
		self._card_container.scale(default_scale, default_scale)

		self._aligner_selector.currentTextChanged.connect(
			self._align_change
		)

		box = QtWidgets.QVBoxLayout(self)

		self._tool_bar = QtWidgets.QHBoxLayout(self)

		self._tool_bar.addWidget(self._zone_label)
		self._tool_bar.addWidget(self._selected_info)
		self._tool_bar.addWidget(self._aligner_selector)

		self._selected_info.set_amount_selected()

		box.addLayout(self._tool_bar)
		box.addWidget(self._card_container)

		self.setLayout(box)

	def _align_change(self, s: str) -> None:
		aligners = {
			'Stacking Grid': StaticStackingGrid,
			'Grid': GridAligner,
		}

		self._undo_stack.push(
			ChangeAligner(
				self.card_container.scene(),
				aligners[s](
					self.card_container.scene(),
					self._undo_stack,
				),
			)
		)

	def selection_change(self):
		self._selected_info.set_amount_selected(
			len(self._card_container.scene().selectedItems())
		)

	@property
	def card_container(self) -> CardContainer:
		return self._card_container

	@property
	def undo_stack(self) -> UndoStack:
		return self._undo_stack

	@property
	def printings(self) -> t.Iterable[Printing]:
		return (card.printing for card in self._card_container.card_scene.cards)

