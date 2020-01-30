import pickle
import typing as t

import os
import uuid
from pickle import UnpicklingError

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

from deckeditor.values import SUPPORTED_EXTENSIONS
from magiccube.collections.cube import Cube

from deckeditor import paths
from deckeditor.components.views.editables.deck import DeckView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.models.deck import DeckModel, PoolModel
from deckeditor.serialization.deckserializer import DeckSerializer


class EditablesMeta(object):

    def __init__(self, name: str, path: t.Optional[str] = None):
        self._path: t.Optional[str] = path
        self._key = str(uuid.uuid4())
        self._name: str = name

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        self._name = os.path.splitext(os.path.split(value)[1])[0]
        self._path = value

    @property
    def key(self) -> str:
        return self._key

    @property
    def name(self) -> str:
        return self._name

    @property
    def truncated_name(self) -> str:
        return self._name if len(self._name) <= 25 else self._name[:22] + '...'


class EditablesTabs(QtWidgets.QTabWidget):
    DEFAULT_TEMPLATE = 'New Deck {}'

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self._new_decks = 0

        # self._open_files: t.MutableMapping[str, Editable] = {}
        self._metas: t.MutableMapping[Editable, EditablesMeta] = {}

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
                    'tabs': [
                        (editor.persist(), meta)
                        for editor, meta in
                        self._metas.items()
                    ],
                    'current_tab_index': self.currentIndex(),
                },
                session_file,
            )

    def load(self) -> None:
        try:
            previous_session = pickle.load(open(paths.SESSION_PATH, 'rb'))
        except (FileNotFoundError, UnpicklingError, EOFError):
            return

        for state, meta in previous_session['tabs']:
            self.load_file(state, meta)

        self.setCurrentIndex(previous_session['current_tab_index'])

    def add_editable(self, editable: Editable, meta: EditablesMeta) -> Editable:
        self.addTab(editable, meta.truncated_name)
        self._metas[editable] = meta
        return editable

    def new_deck(self, model: DeckModel) -> DeckView:
        deck_widget = DeckView(model)
        self.add_editable(deck_widget, EditablesMeta('untitled deck'))
        return deck_widget

    def load_file(self, state: t.Any, meta: EditablesMeta) -> Editable:
        return self.add_editable(DeckView.load(state), meta)

    def open_file(self, path: str) -> None:
        for editable, meta in self._metas.items():
            if meta.path == path:
                self.setCurrentWidget(editable)
                return

        file_name = os.path.split(path)[1]
        name, extension = os.path.splitext(file_name)
        extension = extension[1:]
        meta = EditablesMeta(file_name, path)

        if extension.lower() == 'embd':
            with open(path, 'rb') as f:
                deck_view = self.load_file(pickle.load(f), meta)

        else:
            with open(path, 'r') as f:
                deck = DeckSerializer.extension_to_serializer[extension].deserialize(f.read())

            deck_view = DeckView(
                DeckModel(
                    CubeScene(StaticStackingGrid, deck.maindeck),
                    CubeScene(StaticStackingGrid, deck.sideboard),
                )
            )
            self.add_editable(deck_view, meta)

        self.setCurrentWidget(deck_view)

    def save_tab_at_path(self, editable: Editable, path: str) -> None:
        extension = path.split('.')[1]

        with open(path, 'w') as f:
            f.write(
                DeckSerializer.extension_to_serializer[extension].serialize(
                    editable.deck_model.as_deck()
                )
            )

        editable.undo_stack.clear()

        self._metas[editable].path = path
        self.setTabText(
            self.indexOf(editable),
            self._metas[editable].truncated_name,
        )

    def save_tab(self, editable: t.Optional[Editable] = None):
        current_editable: DeckView = editable if editable is not None else self.currentWidget()

        if not current_editable or not isinstance(current_editable, DeckView):
            return

        meta = self._metas[current_editable]

        if not meta.path:
            self.save_tab_as()
            return

        self.save_tab_at_path(current_editable, meta.path)

    def save_tab_as(self, editable: t.Optional[Editable] = None) -> None:
        current_editable: DeckView = editable if editable is not None else self.currentWidget()

        if not current_editable or not isinstance(current_editable, DeckView):
            return

        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dialog.setNameFilter(SUPPORTED_EXTENSIONS)
        dialog.setDefaultSuffix('json')

        if not dialog.exec_():
            return

        file_names = dialog.selectedFiles()

        if not file_names:
            return

        self.save_tab_at_path(current_editable, file_names[0])


    def _tab_close_requested(self, index: int) -> None:
        closed_tab: DeckView = self.widget(index)

        if not self._metas[closed_tab].path or not closed_tab.undo_stack.isClean():
            confirm_dialog = QMessageBox()
            confirm_dialog.setText('Deck has been modified')
            confirm_dialog.setInformativeText('Wanna save that shit?')
            confirm_dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            confirm_dialog.setDefaultButton(QMessageBox.Cancel)
            return_code = confirm_dialog.exec_()

            if return_code == QMessageBox.Save:
                self.save_tab(closed_tab)
            elif return_code == QMessageBox.Cancel:
                return

        del self._metas[closed_tab]

        if not self.widget(1):
            self.new_deck(DeckModel())

        self.removeTab(index)
