import typing as t
import pickle
import os
import uuid
from pickle import UnpicklingError

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

from deckeditor.components.draft.view import DraftView, DraftModel
from deckeditor.components.editables.editor import Editor
from mtgorp.models.serilization.serializeable import SerializationException

from magiccube.collections.cube import Cube

from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.values import SUPPORTED_EXTENSIONS
from deckeditor.components.views.editables.deck import DeckView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.context.context import Context
from deckeditor.models.deck import DeckModel, PoolModel, TabModel, Deck, Pool
from deckeditor.serialization.tabmodelserializer import TabModelSerializer
from deckeditor import paths


class FileIOException(Exception):
    pass


class FileOpenException(FileIOException):
    pass


class FileSaveException(FileIOException):
    pass


class EditablesMeta(object):

    def __init__(self, name: str, path: t.Optional[str] = None, key: t.Optional[str] = None):
        self._path: t.Optional[str] = path
        self._key = key if key is not None else str(uuid.uuid4())
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


class EditablesTabs(QtWidgets.QTabWidget, Editor):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self._new_decks = 0

        self._metas: t.MutableMapping[Editable, EditablesMeta] = {}

        self.setTabsClosable(True)

        Context.new_pool.connect(self.new_pool)
        Context.draft_started.connect(self.new_draft)
        self.tabCloseRequested.connect(self._tab_close_requested)
        self.currentChanged.connect(self._on_current_changed)

    def current_editable(self) -> t.Optional[Editable]:
        return self.currentWidget()

    def _on_current_changed(self, idx: int) -> None:
        Context.undo_group.setActiveStack(
            self.widget(idx).undo_stack
        )

    def new_draft(self, draft_id: str) -> None:
        for editable, meta in self._metas.items():
            if meta.key == draft_id:
                self.setCurrentWidget(editable)
                return

        self.setCurrentWidget(
            self.add_editable(
                DraftView(
                    DraftModel(
                        draft_id
                    )
                ),
                EditablesMeta(
                    'some draft',
                    key = draft_id,
                ),
            )
        )

    def new_pool(self, pool: Cube, key: str) -> None:
        for editable, meta in self._metas.items():
            if meta.key == key:
                self.setCurrentWidget(editable)
                return

        self.setCurrentWidget(
            self.add_editable(
                PoolView(
                    PoolModel(
                        list(map(PhysicalCard.from_cubeable, pool)),
                    )
                ),
                EditablesMeta(
                    key,
                    key = key,
                ),
            )
        )

    def save_session(self) -> None:
        with open(paths.SESSION_PATH, 'wb') as session_file:
            pickle.dump(
                {
                    'tabs': [
                        (persisted, meta)
                        for persisted, meta in
                        (
                            (editor.persist(), meta)
                            for editor, meta in
                            self._metas.items()
                        )
                        if persisted is not None
                    ],
                    'current_tab_index': self.currentIndex(),
                },
                session_file,
            )

    def load_session(self) -> None:
        try:
            try:
                previous_session = pickle.load(open(paths.SESSION_PATH, 'rb'))
            except FileNotFoundError:
                return
            except (UnpicklingError, EOFError):
                Context.notification_message.emit('Failed loading previous session')
                return
            for state, meta in previous_session['tabs']:
                self.load_file(state, meta)

        except Exception as e:
            confirm_dialog = QMessageBox()
            confirm_dialog.setText('Corrupt session')
            confirm_dialog.setInformativeText(
                'Persistent session is corrupt. This may be due to backward incompatible changes in Embargo Edit.\n'
                'Would you like to delete the session (manual restart still required because good software).'
            )
            confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm_dialog.setDefaultButton(QMessageBox.Yes)
            return_code = confirm_dialog.exec_()

            if return_code == QMessageBox.Yes:
                os.remove(paths.SESSION_PATH)

            raise e

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
        return self.add_editable(
            (
                PoolView
                if state['tab_type'] == 'pool' else
                DeckView
            ).load(state),
            meta,
        )

    def open_file(self, path: str, target: t.Type[TabModel] = Deck) -> None:
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
                try:
                    tab = self.load_file(pickle.load(f), meta)
                except UnpicklingError:
                    raise FileOpenException('corrupt file')

        elif extension.lower() == 'embp':
            with open(path, 'rb') as f:
                try:
                    tab = self.load_file(pickle.load(f), meta)
                except UnpicklingError:
                    raise FileOpenException('corrupt file')

        else:
            with open(path, 'r') as f:
                try:
                    serializer: TabModelSerializer[t.Union[Deck, Pool]] = TabModelSerializer.extension_to_serializer[
                        (extension, target)
                    ]
                except KeyError:
                    raise FileOpenException('unsupported file type "{}"'.format(extension))

                try:
                    tab_model = serializer.deserialize(f.read())
                except SerializationException:
                    raise FileOpenException()

            if target == Deck:
                tab = DeckView(
                    DeckModel(
                        list(map(PhysicalCard.from_cubeable, tab_model.maindeck)),
                        list(map(PhysicalCard.from_cubeable, tab_model.sideboard)),
                    )
                )

            elif target == Pool:
                tab = PoolView(
                    PoolModel(
                        list(map(PhysicalCard.from_cubeable, tab_model)),
                    )
                )

            else:
                raise FileOpenException('invalid load target "{}"'.format(target))

            self.add_editable(tab, meta)

        self.setCurrentWidget(tab)

    def save_tab_at_path(self, editable: Editable, path: str, clear_undo: bool = True) -> None:
        extension = os.path.splitext(path)[-1][1:]

        if isinstance(editable, PoolView):
            if extension == 'embp':
                with open(path, 'wb') as f:
                    pickle.dump(editable.persist(), f)
                return

            try:
                serializer: TabModelSerializer[Pool] = TabModelSerializer.extension_to_serializer[
                    (extension, Pool)
                ]
            except KeyError:
                raise FileSaveException('invalid file type "{}"'.format(extension))

            with open(path, 'w') as f:
                f.write(serializer.serialize(editable.pool_model.as_pool()))

        else:
            if extension == 'embd':
                with open(path, 'wb') as f:
                    pickle.dump(editable.persist(), f)
                return

            try:
                serializer: TabModelSerializer[Deck] = TabModelSerializer.extension_to_serializer[
                    (extension, Deck)
                ]
            except KeyError:
                raise FileSaveException('invalid file type "{}"'.format(extension))

            serialized = serializer.serialize(editable.deck_model.as_deck())
            with open(path, 'w' if isinstance(serialized, str) else 'wb') as f:
                f.write(serialized)

        if clear_undo:
            editable.undo_stack.clear()

            self._metas[editable].path = path
            self.setTabText(
                self.indexOf(editable),
                self._metas[editable].truncated_name,
            )

    def save_tab(self, editable: t.Optional[Editable] = None):
        current_editable = editable if editable is not None else self.currentWidget()

        if not current_editable:
            return

        meta = self._metas[current_editable]

        if not meta.path:
            self.save_tab_as(editable)
            return

        self.save_tab_at_path(current_editable, meta.path)

    def _save_dialog(self, default_suffix: str = 'json') -> t.Tuple[QtWidgets.QFileDialog, int]:
        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dialog.setNameFilter(SUPPORTED_EXTENSIONS)
        dialog.setDefaultSuffix(default_suffix)
        return dialog, dialog.exec_()

    def save_tab_as(self, editable: t.Optional[Editable] = None, clear_undo: bool = True) -> None:
        current_editable = editable if editable is not None else self.currentWidget()

        if not current_editable:
            return

        dialog, result = self._save_dialog()

        if not result:
            return

        file_names = dialog.selectedFiles()

        if not file_names:
            return

        self.save_tab_at_path(current_editable, file_names[0], clear_undo = clear_undo)

    def export_deck(self) -> None:
        current_editable = self.currentWidget()

        if not current_editable:
            return

        if isinstance(current_editable, DeckView):
            self.save_tab_as(current_editable, clear_undo = False)

        elif isinstance(current_editable, PoolView):
            dialog, result = self._save_dialog()

            if not result:
                return

            file_names = dialog.selectedFiles()

            if not file_names:
                return

            extension = os.path.splitext(file_names[0])[-1][1:]

            try:
                serializer: TabModelSerializer[Deck] = TabModelSerializer.extension_to_serializer[
                    (extension, Deck)
                ]
            except KeyError:
                raise FileSaveException('invalid file type "{}"'.format(extension))

            with open(file_names[0], 'w') as f:
                f.write(serializer.serialize(current_editable.pool_model.as_deck()))

    def _tab_close_requested(self, index: int) -> None:
        closed_tab = self.widget(index)

        if not self._metas[closed_tab].path and not closed_tab.is_empty() or not closed_tab.undo_stack.isClean():
            confirm_dialog = QMessageBox()
            confirm_dialog.setText('File has been modified')
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
