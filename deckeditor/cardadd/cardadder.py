

from PyQt5 import QtWidgets

from mtgorp.tools.parsing.search.parse import SearchParser, SearchPatternParseException


class CardAdder(QtWidgets.QWidget):

	def __init__(self):
		super().__init__()

		self._query_edit = QtWidgets.QLineEdit()
		self._search_button = QtWidgets.QPushButton()
		self._result_list = QtWidgets.QListView()

		self._search_button.setText('Search')

		self._top_bar = QtWidgets.QHBoxLayout()
		self._layout = QtWidgets.QVBoxLayout()

		self._top_bar.addWidget(self._query_edit)
		self._top_bar.addWidget(self._search_button)

		self._layout.addLayout(self._top_bar)
		self._layout.addWidget(self._result_list)

		self.setLayout(self._layout)

	def search(self, s: str) -> None:
		pass