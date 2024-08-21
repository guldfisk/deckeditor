import typing as t

from mtgimg.interface import IMAGE_SIZE_MAP, SizeSlug
from mtgorp.models.interfaces import Cardboard, Printing
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from deckeditor.components.cardadd.cardadder import CardboardSelector
from deckeditor.models.focusables.lists import ExpansionPrintingList
from deckeditor.utils.dialogs import SingleInstanceDialog
from deckeditor.views.focusables.multi import FocusableMultiView


class SelectOneOfPrintingsDialog(QDialog):
    cubeable_selected = pyqtSignal(object)

    def __init__(self, printings: t.Sequence[Printing]):
        super().__init__()
        self.setWindowTitle("Select cubeable")

        self._list_model = ExpansionPrintingList(printings)

        self._view = FocusableMultiView(image_mode=True, image_size=SizeSlug.SMALL)
        self._view.set_model(self._list_model)
        self._view.focusable_selected.connect(self._on_cubeable_clicked)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._view)

        width, height = IMAGE_SIZE_MAP[frozenset((SizeSlug.SMALL, False))]

        self.resize(int(width * 3.25), height * 2)

    def _on_cubeable_clicked(self, printings: Printing) -> None:
        self.cubeable_selected.emit(printings)
        self.accept()


class SelectCardboardDialog(SingleInstanceDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Cardboard")

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
