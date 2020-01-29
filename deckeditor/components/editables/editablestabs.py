import json
import pickle
import typing as t

import os
from pickle import UnpicklingError

from PyQt5 import QtWidgets

from deckeditor import paths
from deckeditor.components.views.editables.deck import DeckView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.models.deck import DeckModel, PoolModel
from deckeditor.serialization.deckserializer import DeckSerializer
from magiccube.collections.cube import Cube


class EditablesTabs(QtWidgets.QTabWidget):
    DEFAULT_TEMPLATE = 'New Deck {}'

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self._new_decks = 0

        self._open_files: t.MutableMapping[str, Editable] = {}

        self.setTabsClosable(True)

        Context.new_pool.connect(self._new_pool)
        self.tabCloseRequested.connect(self._tab_close_requested)
        self.currentChanged.connect(self._on_current_changed)

    def _on_current_changed(self, idx: int) -> None:
        Context.undo_group.setActiveStack(
            self.widget(idx).undo_stack
        )

    def _new_pool(self, pool: Cube) -> None:
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

    def save(self) -> None:
        with open(paths.SESSION_PATH, 'wb') as session_file:
            pickle.dump(
                {
                    'tabs': {
                        path: editor.persist()
                        for path, editor in
                        self._open_files.items()
                    },
                    'current_tab_index': self.currentIndex(),
                },
                session_file,
            )

    def load(self) -> None:
        try:
            previous_session = pickle.load(open(paths.SESSION_PATH, 'rb'))
        except (FileNotFoundError, UnpicklingError, EOFError):
            return

        for path, state in previous_session['tabs'].items():
            self.load_file(path, state)

        self.setCurrentIndex(previous_session['current_tab_index'])

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

    def load_file(self, path: str, state: t.Any):
        file_name = os.path.split(path)[1]
        deck_view = DeckView.load(state)
        self._open_files[path] = deck_view
        self.addTab(deck_view, file_name if len(file_name) <= 25 else file_name[:22] + '...')
        return deck_view

    def open_file(self, path: str) -> None:
        if path in self._open_files:
            self.setCurrentWidget(
                self._open_files[path]
            )
            return

        file_name = os.path.split(path)[1]
        name, extension = os.path.splitext(file_name)

        extension = extension[1:]

        if extension.lower() == 'embd':
            with open(path, 'rb') as f:
                deck_view = self.load_file(path, f)

        else:
            with open(path, 'r') as f:
                deck = DeckSerializer.extension_to_serializer[extension].deserialize(f.read())

            deck_view = DeckView(
                DeckModel(
                    CubeScene(StaticStackingGrid, deck.maindeck),
                    CubeScene(StaticStackingGrid, deck.sideboard),
                )
            )

            self.addTab(deck_view, file_name if len(file_name) <= 25 else file_name[:22] + '...')

            self._open_files[path] = deck_view

        self.setCurrentWidget(deck_view)

    def _tab_close_requested(self, index: int) -> None:
        closed_tab = self.widget(index)
        for path, editor in self._open_files.items():
            if editor == closed_tab:
                del self._open_files[path]
                break

        self.removeTab(index)

        if not self.widget(0):
            self.new_deck(DeckModel())
