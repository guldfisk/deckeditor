import os
import pickle
import sys
import threading
import typing as t
from pickle import UnpicklingError

from cubeclient.models import LimitedDeck
from magiccube.collections.cube import Cube
from magiccube.collections.infinites import Infinites
from mtgorp.models.serilization.serializeable import SerializationException
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QUndoStack

from deckeditor import paths
from deckeditor.application.embargo import restart
from deckeditor.components.draft.view import DraftModel, DraftView
from deckeditor.components.editables.editor import Editor, TabMeta
from deckeditor.components.settings import settings
from deckeditor.components.views.editables.deck import DeckView
from deckeditor.components.views.editables.editable import Editable, Tab, TabType
from deckeditor.components.views.editables.multicubesview import MultiCubesView
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.context.context import Context
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.deck import Deck, DeckModel, Pool, PoolModel, TabModel
from deckeditor.serialization.tabmodelserializer import TabModelSerializer
from deckeditor.utils.actions import WithActions
from deckeditor.utils.wrappers import notify_on_exception
from deckeditor.values import SUPPORTED_EXTENSIONS


class FileIOException(Exception):
    pass


class FileOpenException(FileIOException):
    pass


class FileSaveException(FileIOException):
    pass


class EditablesTabBar(QtWidgets.QTabBar):
    tab_close_requested = pyqtSignal(int)

    def mousePressEvent(self, mouse_event: QtGui.QMouseEvent) -> None:
        if mouse_event.button() & QtCore.Qt.MiddleButton:
            tab_bar_index = self.tabAt(mouse_event.pos())
            if tab_bar_index != -1:
                self.tab_close_requested.emit(tab_bar_index)
        else:
            super().mousePressEvent(mouse_event)


def load_editable(serialized: t.Mapping[str, t.Any], undo_stack: t.Optional[QUndoStack] = None) -> Editable:
    return (PoolView if serialized["tab_type"] == TabType.POOL else DeckView).load(
        serialized, undo_stack or Context.get_undo_stack()
    )


class EditorTab(Tab):
    editable_loaded = pyqtSignal(Editable)

    def __init__(
        self,
        editable: t.Union[Editable, t.Mapping[str, t.Any]],
        undo_stack: t.Optional[QUndoStack] = None,
    ) -> None:
        super().__init__(Context.get_undo_stack() if undo_stack is None else undo_stack)

        self._loading_lock = threading.Lock()
        self._loading_event = threading.Event()
        self._loading = False

        if isinstance(editable, Editable):
            self._editable = editable
            self._serialized = None
        else:
            self._editable = None
            self._serialized = editable

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._loading_label = None

        if self._editable is None:
            self._loading_label = QtWidgets.QLabel("Loading...")
            self._loading_label.setAlignment(QtCore.Qt.AlignCenter)
            self._layout.addWidget(self._loading_label)
            self.editable_loaded.connect(self._on_loaded)
        else:
            self._layout.addWidget(self._editable)
            self._editable.tab = self
            self._editable.show()

    def _on_loaded(self, editable: Editable):
        self._serialized = None
        self._layout.removeWidget(self._loading_label)
        self._loading_label.deleteLater()
        self._loading_label = None
        self._layout.addWidget(self._editable)

    def load(self) -> None:
        if self._editable:
            return

        with self._loading_lock:
            if self._loading:
                return
            self._loading = True

        self._load()

    @property
    def undo_stack(self) -> QUndoStack:
        if self._editable:
            return self._editable.undo_stack
        return self._undo_stack

    def _load(self) -> None:
        with self._loading_lock:
            try:
                self._editable = load_editable(self._serialized, self._undo_stack)
            except Exception:
                if Context.debug:
                    import traceback

                    traceback.print_exc()
                Context.notification_message.emit("Failed loading tab")
                self._editable = DeckView(DeckModel(), self._undo_stack)

            self._editable.tab = self

            self._loading = False
            self._loading_event.set()
            self.editable_loaded.emit(self._editable)

    @property
    def loaded(self) -> bool:
        return self._editable is not None

    @property
    def editable(self) -> Editable:
        if self._editable is None:
            self.load()
            self._loading_event.wait()

        return self._editable

    def persist(self) -> t.Any:
        if self._editable is not None:
            return self._editable.persist()
        return self._serialized

    @property
    def tab_type(self) -> str:
        if self._editable is not None:
            return self._editable.tab_type
        return self._serialized["tab_type"]


class EditablesTabs(QtWidgets.QTabWidget, Editor, WithActions):
    tabBar: t.Callable[[], EditablesTabBar]
    currentWidget: t.Callable[[], t.Optional[Tab]]

    new_remote_deck = pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self.setTabBar(EditablesTabBar())
        self._new_decks = 0

        self._metas: t.MutableMapping[Tab, TabMeta] = {}

        self.setMovable(True)
        self.setContentsMargins(1, 2, 1, 1)

        Context.new_pool.connect(self.new_pool)
        Context.draft_started.connect(self.new_draft)
        Context.open_file.connect(self.open_file)

        self.tabBar().tab_close_requested.connect(self.tabCloseRequested)
        self.tabCloseRequested.connect(self._tab_close_requested)
        self.currentChanged.connect(self._on_current_changed)

        for n in range(1, 8):
            self._create_action(f"Go to tab {n}", self._get_go_to_tab(n - 1), f"Alt+{n}")

        self._create_action("Go to last tab", self.go_to_last_tab, "Alt+9")

        self.new_remote_deck.connect(self.new_limited_deck)

    def _get_go_to_tab(self, idx: int) -> t.Callable[[], None]:
        return lambda: self.setCurrentIndex(idx)

    def go_to_last_tab(self) -> None:
        self.setCurrentIndex(self.count() - 1)

    def current_editable(self) -> t.Optional[Editable]:
        tab = self.currentWidget()
        if tab:
            return tab.editable

    def _on_current_changed(self, idx: int) -> None:
        tab: Tab = self.widget(idx)
        if tab:
            tab.load()
            Context.undo_group.setActiveStack(tab.undo_stack)

    def new_draft(self, draft_id: str) -> None:
        for editable, meta in self._metas.items():
            if meta.key == draft_id:
                self.setCurrentWidget(editable)
                return

        saved_draft = Context.saved_drafts.pop(draft_id, None)

        self.setCurrentWidget(
            self.add_editable(
                (
                    DraftView.load(saved_draft, Context.get_undo_stack())
                    if saved_draft is not None
                    else DraftView(
                        DraftModel(draft_id),
                        Context.get_undo_stack(),
                    )
                ),
                TabMeta(
                    "some draft",
                    key=draft_id,
                ),
            )
        )

    def new_pool(self, pool: Cube, infinites: Infinites, key: str) -> None:
        for tab, meta in self._metas.items():
            if meta.key == key:
                self.setCurrentWidget(tab)
                return

        tab = self.add_editable(
            PoolView(
                PoolModel(
                    list(map(PhysicalCard.from_cubeable, pool)),
                    infinites=infinites,
                ),
                undo_stack=Context.get_undo_stack(),
            ),
            TabMeta(
                key,
                key=key,
            ),
        )
        self.setCurrentWidget(tab)

        self._sort_opened_view(tab.editable)

    def _check_for_key(self, key: str) -> bool:
        for editable, meta in self._metas.items():
            if meta.key == key:
                self.setCurrentWidget(editable)
                return True
        return False

    def new_limited_deck(self, deck: LimitedDeck) -> None:
        key = f"pool-deck-{deck.id}"
        if self._check_for_key(key):
            return

        tab = self.add_editable(
            DeckView(
                DeckModel(
                    list(map(PhysicalCard.from_cubeable, deck.deck.maindeck)),
                    list(map(PhysicalCard.from_cubeable, deck.deck.sideboard)),
                ),
                undo_stack=Context.get_undo_stack(),
            ),
            TabMeta(
                deck.name,
                key=key,
            ),
        )

        self.setCurrentWidget(tab)

        self._sort_opened_view(tab.editable)

    def open_limited_deck(self, deck_id: t.Union[str, int]) -> None:
        if self._check_for_key(f"pool-deck-{deck_id}"):
            return

        if Context.cube_api_client:
            Context.cube_api_client.limited_deck(deck_id).then(self.new_remote_deck.emit).catch(
                lambda e: Context.notification_message.emit("Failed retrieving deck")
            )
        else:
            Context.notification_message.emit("Cannot fetch deck")

    @classmethod
    def _get_session_path(cls) -> str:
        return paths.DEBUG_SESSION_PATH if Context.debug else paths.SESSION_PATH

    def save_session(self) -> None:
        with open(self._get_session_path(), "wb") as session_file:
            tabs = []
            drafts = {}
            for tab, meta in self._metas.items():
                if tab.tab_type == TabType.DRAFT:
                    drafts[meta.key] = tab.persist()
                else:
                    tabs.append((tab.persist(), meta))
            pickle.dump(
                {
                    "tabs": tabs,
                    "drafts": drafts,
                    "current_tab_index": self.currentIndex(),
                },
                session_file,
            )

    def load_session(self) -> None:
        try:
            self.currentChanged.disconnect(self._on_current_changed)
            try:
                previous_session = pickle.load(open(self._get_session_path(), "rb"))
            except FileNotFoundError:
                return
            except (UnpicklingError, EOFError):
                Context.notification_message.emit("Failed loading previous session")
                return

            for state, meta in previous_session["tabs"]:
                self.load_file(state, meta)

            Context.saved_drafts = previous_session.get("drafts", {})

        except Exception:
            if Context.debug:
                import traceback

                traceback.print_exc()
            confirm_dialog = QMessageBox()
            confirm_dialog.setText("Corrupt session")
            confirm_dialog.setInformativeText(
                "Persistent session is corrupt. This may be due to backward incompatible changes in Embargo Edit.\n"
                "Would you like to delete the session?"
            )
            confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm_dialog.setDefaultButton(QMessageBox.Yes)
            return_code = confirm_dialog.exec_()

            if return_code == QMessageBox.Yes:
                os.remove(self._get_session_path())
                restart(save_session=False)
            else:
                sys.exit()

            return

        idx = previous_session["current_tab_index"]
        self.setCurrentIndex(idx)
        self._on_current_changed(self.currentIndex())
        self.currentChanged.connect(self._on_current_changed)

    def add_editable(self, editable: t.Union[Editable, t.Mapping[str, t.Any]], meta: TabMeta) -> Tab:
        tab = EditorTab(
            editable,
            editable.undo_stack if isinstance(editable, Editable) else Context.get_undo_stack(),
        )
        self.addTab(tab, meta.truncated_name)
        self._metas[tab] = meta
        return tab

    def new_deck(self, model: DeckModel) -> Tab:
        return self.add_editable(
            DeckView(model, Context.get_undo_stack()),
            TabMeta("untitled deck"),
        )

    def load_file(self, state: t.Any, meta: TabMeta) -> Tab:
        return self.add_editable(
            state if settings.LAZY_TABS.get_value() else load_editable(state),
            meta,
        )

    def _sort_opened_view(self, editable: Editable) -> None:
        if isinstance(editable, MultiCubesView) and settings.AUTO_SORT_NON_EMB_FILES_ON_OPEN.get_value():
            for cube_view in editable.cube_views:
                cube_view.cube_scene.get_default_sort().redo()

        for cube_view in editable.cube_views:
            cube_view.cube_image_view.fit_cards()

    @notify_on_exception(
        (FileNotFoundError, FileOpenException),
        lambda e: "File not found" if isinstance(e, FileNotFoundError) else ", ".join(map(str, e.args)),
    )
    def open_file(self, path: str, target: t.Type[TabModel] = Deck) -> None:
        for editable, meta in self._metas.items():
            if meta.path == path:
                self.setCurrentWidget(editable)
                return

        file_name = os.path.split(path)[1]
        name, extension = os.path.splitext(file_name)
        extension = extension[1:]
        meta = TabMeta(file_name, path)
        editable = None

        if extension.lower() == "embd":
            with open(path, "rb") as f:
                try:
                    tab = self.load_file(pickle.load(f), meta)
                except UnpicklingError:
                    raise FileOpenException("corrupt file")

        elif extension.lower() == "embp":
            with open(path, "rb") as f:
                try:
                    tab = self.load_file(pickle.load(f), meta)
                except UnpicklingError:
                    raise FileOpenException("corrupt file")

        else:
            with open(path, "r") as f:
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
                editable = DeckView(
                    DeckModel(
                        list(map(PhysicalCard.from_cubeable, tab_model.maindeck)),
                        list(map(PhysicalCard.from_cubeable, tab_model.sideboard)),
                    ),
                    Context.get_undo_stack(),
                )

            elif target == Pool:
                editable = PoolView(
                    PoolModel(
                        list(map(PhysicalCard.from_cubeable, tab_model)),
                    ),
                    Context.get_undo_stack(),
                )

            else:
                raise FileOpenException('invalid load target "{}"'.format(target))

            tab = self.add_editable(editable, meta)

        self.setCurrentWidget(tab)

        if editable is not None:
            self._sort_opened_view(editable)

        if not Context.main_window.isActiveWindow() and Context.settings.value("focus_on_open_file", True, bool):
            Context.main_window.raise_()
            Context.main_window.show()
            Context.main_window.activateWindow()

    def save_tab_at_path(self, tab: Tab, path: str, clear_undo: bool = True) -> None:
        extension = os.path.splitext(path)[-1][1:]

        if tab.tab_type == TabType.POOL:
            if extension == "embp":
                with open(path, "wb") as f:
                    pickle.dump(tab.persist(), f)
                return

            try:
                serializer: TabModelSerializer[Pool] = TabModelSerializer.extension_to_serializer[(extension, Pool)]
            except KeyError:
                try:
                    serializer: TabModelSerializer[Deck] = TabModelSerializer.extension_to_serializer[
                        (extension, Deck)
                    ]
                except KeyError:
                    raise FileSaveException('invalid file type "{}"'.format(extension))

                serialized = serializer.serialize(tab.editable.pool_model.as_deck())
                with open(path, "w" if isinstance(serialized, str) else "wb") as f:
                    f.write(serialized)

                return

            with open(path, "w") as f:
                f.write(serializer.serialize(tab.editable.pool_model.as_pool()))

        else:
            if extension == "embd":
                with open(path, "wb") as f:
                    pickle.dump(tab.persist(), f)
                return

            try:
                serializer: TabModelSerializer[Deck] = TabModelSerializer.extension_to_serializer[(extension, Deck)]
            except KeyError:
                raise FileSaveException('invalid file type "{}"'.format(extension))

            serialized = serializer.serialize(tab.editable.deck_model.as_deck())
            with open(path, "w" if isinstance(serialized, str) else "wb") as f:
                f.write(serialized)

        if clear_undo:
            tab.undo_stack.clear()

            self._metas[tab].path = path
            self.setTabText(
                self.indexOf(tab),
                self._metas[tab].truncated_name,
            )

    def save_tab(self, tab: t.Optional[Tab] = None):
        current_tab = tab if tab is not None else self.currentWidget()

        if not current_tab:
            return

        meta = self._metas[current_tab]

        if not meta.path:
            self.save_tab_as(tab)
            return

        self.save_tab_at_path(current_tab, meta.path)

    def _save_dialog(self, default_suffix: str = "json") -> t.Tuple[QtWidgets.QFileDialog, int]:
        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dialog.setNameFilter(SUPPORTED_EXTENSIONS)
        dialog.setDefaultSuffix(default_suffix)
        return dialog, dialog.exec_()

    def save_tab_as(self, tab: t.Optional[Tab] = None, clear_undo: bool = True) -> None:
        current_tab = tab if tab is not None else self.currentWidget()

        if not current_tab:
            return

        dialog, result = self._save_dialog()

        if not result:
            return

        file_names = dialog.selectedFiles()

        if not file_names:
            return

        self.save_tab_at_path(current_tab, file_names[0], clear_undo=clear_undo)

    def export_deck(self) -> None:
        current_tab = self.currentWidget()

        if not current_tab:
            return

        if current_tab.tab_type == TabType.DECK:
            self.save_tab_as(current_tab, clear_undo=False)

        elif current_tab.tab_type == TabType.POOL:
            dialog, result = self._save_dialog()

            if not result:
                return

            file_names = dialog.selectedFiles()

            if not file_names:
                return

            extension = os.path.splitext(file_names[0])[-1][1:]

            try:
                serializer: TabModelSerializer[Deck] = TabModelSerializer.extension_to_serializer[(extension, Deck)]
            except KeyError:
                raise FileSaveException('invalid file type "{}"'.format(extension))

            with open(file_names[0], "w") as f:
                f.write(serializer.serialize(current_tab.editable.pool_model.as_deck()))

    def close_tab(self, tab: Tab) -> None:
        del self._metas[tab]

        if tab.loaded:
            tab.editable.close()

        if not self.widget(1):
            self.new_deck(DeckModel())

        self.removeTab(self.indexOf(tab))

    def _tab_close_requested(self, index: int) -> None:
        closed_tab: Tab = self.widget(index)

        if settings.CONFIRM_CLOSING_MODIFIED_FILE.get_value() and (
            not self._metas[closed_tab].path
            and (not closed_tab.loaded or not closed_tab.editable.is_empty() or not closed_tab.undo_stack.isClean())
        ):
            confirm_dialog = QMessageBox()
            confirm_dialog.setText("File has been modified")
            confirm_dialog.setInformativeText("Wanna save that shit?")
            confirm_dialog.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            confirm_dialog.setDefaultButton(QMessageBox.Cancel)
            return_code = confirm_dialog.exec_()

            if return_code == QMessageBox.Save:
                self.save_tab(closed_tab)
            elif return_code == QMessageBox.Cancel:
                return

        self.close_tab(closed_tab)
