import os

from PyQt5 import QtWidgets, QtCore, QtSvg
from PyQt5.QtCore import Qt

from deckeditor import paths


class Notification(QtWidgets.QFrame):

	signal = QtCore.pyqtSignal(QtWidgets.QWidget)

	def __init__(self, parent, message: str):
		super().__init__(parent)

		self.setWindowFlags(Qt.FramelessWindowHint)
		# self.setWindowModality(Qt.WindowModal)

		self._label = QtWidgets.QLabel(self)
		self._icon = QtSvg.QSvgWidget(
			os.path.join(
				paths.RESOURCE_PATH,
				'exclamation_mark.svg',
			)
		)

		self._label.setText(message)
		self._label.setWordWrap(True)

		self._icon.setFixedSize(20, 20)

		self.setFixedSize(300, 150)

		self._layout = QtWidgets.QHBoxLayout()

		self._layout.addWidget(self._icon, alignment=Qt.AlignTop)
		self._layout.addWidget(self._label, alignment=Qt.AlignTop)

		self.setLayout(self._layout)

	def mouseReleaseEvent(self, release_event):
		self.signal.emit(self)

