import typing

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QUndoStack

from deckeditor.components.views.cubeedit.cubelistview import CubeListView
from deckeditor.components.views.cubeedit.graphical.cubemultiimageview import CubeMultiImageView
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.components.views.editables.editable import Editable
from deckeditor.context.context import Context
from deckeditor.models.deck import DeckModel


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
            CubeMultiImageView(
                self._deck_model.maindeck,
                self._undo_stack,
            )
        )

        layout.addWidget(horizontal_splitter)

        self.setLayout(layout)

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack
