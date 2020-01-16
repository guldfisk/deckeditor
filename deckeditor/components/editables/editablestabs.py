from PyQt5 import QtWidgets

from deckeditor.components.views.editables.deck import DeckView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.models.deck import DeckModel, PoolModel
from magiccube.collections.cube import Cube


class EditablesTabs(QtWidgets.QTabWidget):
    DEFAULT_TEMPLATE = 'New Deck {}'

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self._new_decks = 0
        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self._tab_close_requested)
        Context.new_pool.connect(self._new_pool)
        # self.currentChanged.connect(self._current_changed)

    def _new_pool(self, pool: Cube):
        self.addTab(
            PoolView(
                PoolModel(
                    CubeScene(
                        StaticStackingGrid,
                        pool,
                    )
                )
            ),
            'a pool',
        )

    def add_editable(self, editable: Editable, name: str) -> None:
        self.addTab(editable, name)

    def new_deck(self, model: DeckModel) -> DeckView:
        deck_widget = DeckView(model)
        self.add_editable(
            deck_widget,
            'a deck',
        )
        self._new_decks += 1

        return deck_widget

    def _tab_close_requested(self, index: int) -> None:
        if index == 0:
            self.new_deck(DeckModel())

        self.removeTab(index)

    # def _current_changed(self, index: int) -> None:
    #     Context.deck_list_view.set_deck.emit(
    #         self.currentWidget().maindeck.printings,
    #         self.currentWidget().sideboard.printings,
    #     )
