
from PyQt5 import QtWidgets, QtCore, Qt, QtGui

from deckeditor.cardcontainers.cardcontainer import CardContainer, ChangeAligner
from deckeditor.undo.command import UndoStack

from deckeditor.cardcontainers.alignment.aligner import Aligner
from deckeditor.cardcontainers.alignment.stackinggrid import StackingGrid
from deckeditor.cardcontainers.alignment.grid import GridAligner


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


class CardWindow(QtWidgets.QWidget):

	def __init__(self, undo_stack: UndoStack):
		super().__init__()

		self._undo_stack = undo_stack

		self._slider = ScaleSlider(self)
		self._card_container = CardContainer(self._undo_stack, StackingGrid)
		self._selected_info = SelectedInfo()
		self._aligner_selector = AlignSelector(self)

		self._card_container.scene().selectionChanged.connect(self.selection_change)

		self._slider.valueChanged.connect(
			lambda v:
				self._card_container.setTransform(
					QtGui.QTransform()
					.scale(
						v/100,
						v/100,
					)
				)
		)
		self._slider.setValue(20)

		self._aligner_selector.currentTextChanged.connect(
			self._align_change
		)

		box = QtWidgets.QVBoxLayout(self)

		self._tool_bar = QtWidgets.QHBoxLayout(self)

		self._tool_bar.addWidget(self._selected_info)
		self._tool_bar.addWidget(self._aligner_selector)

		self._selected_info.set_amount_selected()

		box.addLayout(self._tool_bar)
		box.addWidget(self._card_container)
		box.addWidget(self._slider)

		self.setLayout(box)

	def _align_change(self, s: str) -> None:
		alingers = {
			'Stacking Grid': StackingGrid,
			'Grid': GridAligner,
		}

		self._undo_stack.push(
			ChangeAligner(
				self.card_container.scene(),
				alingers[s](
					self.card_container.scene()
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
