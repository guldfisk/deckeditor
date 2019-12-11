from PyQt5 import QtWidgets

from deckeditor.components.views.editables.deck import DeckView
from deckeditor.models.deck import DeckModel


class DeckTabs(QtWidgets.QTabWidget):
    DEFAULT_TEMPLATE = 'New Deck {}'

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self._new_decks = 0
        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self._tab_close_requested)
        # self.currentChanged.connect(self._current_changed)

    def add_deck(self, deck: DeckView) -> None:
        self.addTab(deck, 'a deck')

    def new_deck(self, model: DeckModel) -> DeckView:
        deck_widget = DeckView(model)
        self.add_deck(
            deck_widget
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
