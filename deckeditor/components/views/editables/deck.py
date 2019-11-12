import typing

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QWidget, QLayout, QVBoxLayout

from deckeditor.components.views.cubeedit.cubelistview import CubeListView
from deckeditor.components.views.cubeedit.graphical.alignment.grid import GridAligner
from deckeditor.components.views.cubeedit.graphical.cubeimageview import CubeImageView
from deckeditor.components.views.cubeedit.graphical.cubescene import CubeScene
from deckeditor.components.views.editables.editable import Editable
from deckeditor.models.deck import DeckModel


class DeckView(Editable):

    def __init__(
        self,
        deck_model: DeckModel,
        parent: typing.Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._deck_model = deck_model

        layout = QVBoxLayout()

        horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        horizontal_splitter.addWidget(
            CubeListView(
                self._deck_model.maindeck
            )
        )
        horizontal_splitter.addWidget(
            # CubeListView(
            #     # TODO should be sideboard
            #     self._deck_model.maindeck
            # )
            CubeImageView(
                CubeScene(
                    self._deck_model.maindeck,
                    GridAligner(),
                )
            )
        )

        layout.addWidget(horizontal_splitter)

        self.setLayout(layout)
