import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from mtgorp.models.interfaces import Cardboard

from mtgimg.interface import SizeSlug

from magiccube.collections.cubeable import Cubeable

from deckeditor.models.focusables.grid import CubeablesGrid
from deckeditor.models.focusables.lists import CubeablesList
from deckeditor.views.focusables.grid import FocusableGridView
from deckeditor.components.cardadd.cardadder import CardboardSelector
from deckeditor.utils.dialogs import SingleInstanceDialog


class SelectCubeableDialog(QDialog):
    cubeable_selected = pyqtSignal(object)

    def __init__(self, cubeables: t.Sequence[Cubeable]):
        super().__init__()
        self.setWindowTitle('Select cubeable')

        self._list_model = CubeablesList(cubeables)

        self._table_model = CubeablesGrid()
        self._table_model.setSourceModel(self._list_model)

        self._view = FocusableGridView(SizeSlug.SMALL)
        self._view.setModel(self._table_model)
        self._view.cubeable_clicked.connect(self._on_cubeable_clicked)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._view)

    def _on_cubeable_clicked(self, cubeable: Cubeable) -> None:
        self.cubeable_selected.emit(cubeable)
        self.accept()


class SelectCardboardDialog(SingleInstanceDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Select Cardboard')

        self._cardboard_selector = CardboardSelector()

        self._cardboard_selector.cardboard_selected.connect(self._handle_cardboard_selected)
        self._cardboard_selector.current_cardboard_changed.connect(self._handle_current_cardboard_changed)

        self._cardboard: t.Optional[Cardboard] = None

        layout = QtWidgets.QVBoxLayout(self)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self._buttons.rejected.connect(self.reject)
        self._buttons.accepted.connect(self.accept)

        layout.addWidget(self._cardboard_selector)
        layout.addWidget(self._buttons)

        self.setFocusProxy(self._cardboard_selector)

    def _handle_current_cardboard_changed(self, cardboard: Cardboard) -> None:
        self._cardboard = cardboard

    def _handle_cardboard_selected(self, cardboard: Cardboard) -> None:
        self._cardboard = cardboard
        self.accept()

    @classmethod
    def get_cardboard(cls) -> t.Tuple[t.Optional[Cardboard], bool]:
        dialog = cls.get()
        dialog._cardboard = None
        dialog._cardboard_selector.setFocus()
        if dialog.exec_() and dialog._cardboard:
            return dialog._cardboard, True
        return None, False
