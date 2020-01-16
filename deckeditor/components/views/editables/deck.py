import typing

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QUndoStack

from deckeditor.components.views.cubeedit.cubelistview import CubeListView
from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.context.context import Context
from deckeditor.models.deck import DeckModel
from deckeditor.values import SUPPORTED_EXTENSIONS
from mtgorp.models.serilization.strategies.jsonid import JsonId


class DeckView(Editable):

    def __init__(
        self,
        deck_model: DeckModel,
        parent: typing.Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._undo_stack = QUndoStack(Context.undo_group)
        Context.undo_group.setActiveStack(self._undo_stack)

        self._deck_model = deck_model

        layout = QVBoxLayout()

        horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        horizontal_splitter.addWidget(
            CubeListView(
                self._deck_model.maindeck,
                self._undo_stack,
            )
        )
        horizontal_splitter.addWidget(
            # CubeListView(
            #     # TODO should be sideboard
            #     self._deck_model.maindeck
            # )
            # CubeImageView(
            #     CubeScene(
            #         self._deck_model.maindeck,
            #         StaticStackingGrid,
            #     )
            # )
            CubeView(
                self._deck_model.maindeck,
                self._undo_stack,
            )
        )

        layout.addWidget(horizontal_splitter)

        self.setLayout(layout)

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    def save(self) -> None:
        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dialog.setNameFilter(SUPPORTED_EXTENSIONS)
        dialog.setDefaultSuffix('json')
        # dialog.selectFile('u suck lol')

        if not dialog.exec_():
            return

        file_names = dialog.selectedFiles()

        if not file_names:
            return

        file_name = file_names[0]

        # try:
        #     s = Context.soft_serialization.serialize(
        #         self._main_view.active_deck.deck,
        #         os.path.splitext(file_name)[1][1:],
        #     )
        # except SerializationException:
        #     return

        with open(file_name, 'w') as f:
            f.write(
                JsonId.serialize(self._deck_model.as_deck())
            )