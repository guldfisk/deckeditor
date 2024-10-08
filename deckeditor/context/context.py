import threading
import typing as t
from enum import Enum

from cubeclient.endpoints import AsyncNativeApiClient
from cubeclient.images import ImageClient
from magiccube.collections.cube import Cube
from magiccube.collections.infinites import Infinites
from mtgimg.load import Loader as ImageLoader
from mtgorp.db.database import CardDatabase
from mtgorp.db.load import PickleLoader, SqlLoader
from mtgorp.tools.parsing.search.parse import SearchParser
from mtgqt.pixmapload.pixmaploader import PixmapLoader
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QMainWindow,
    QUndoGroup,
    QUndoStack,
)

from deckeditor.components.cardview.focuscard import FocusEvent
from deckeditor.components.editables.editor import Editor
from deckeditor.context.sql import SqlContext
from deckeditor.sorting.custom import CustomSortMap
from deckeditor.utils.executors import LIFOExecutor


class DbType(Enum):
    DEFAULT = "default"
    PICKLE = "pickle"
    SQL = "sql"


class _Context(QObject):
    debug: bool = False

    settings: QtCore.QSettings
    pixmap_loader: PixmapLoader

    db: CardDatabase

    compiled: bool
    no_ssl_verify: bool

    cardboard_names: t.List[str]
    search_pattern_parser: SearchParser
    undo_group: QUndoGroup
    clipboard: QClipboard
    main_window: QMainWindow
    application: QApplication

    editor: Editor

    token_changed = pyqtSignal(str)

    cube_api_client: AsyncNativeApiClient

    notification_message = pyqtSignal(str)
    status_message = pyqtSignal(str, int)

    focus_card_changed = pyqtSignal(FocusEvent)
    focus_freeze_changed = pyqtSignal(bool)
    focus_card_frozen: bool = False

    focus_scene_changed = pyqtSignal(QGraphicsScene)

    open_file = pyqtSignal(str)

    draft_started = pyqtSignal(object)
    sealed_started = pyqtSignal(int, bool)

    new_pool = pyqtSignal(Cube, Infinites, str)

    saved_drafts: t.Mapping[str, t.Any] = {}

    sort_map: CustomSortMap

    embargo_server: t.Optional[threading.Thread] = None

    @classmethod
    def init(
        cls,
        application: QApplication,
        compiled: bool = True,
        debug: bool = False,
        db_type: DbType = DbType.DEFAULT,
        echo_sql: bool = False,
        no_ssl_verify: bool = False,
    ) -> None:
        cls.debug = debug
        cls.no_ssl_verify = no_ssl_verify
        cls.compiled = compiled

        cls.settings = QtCore.QSettings("lost-world", "Embargo Edit")

        if db_type == DbType.DEFAULT:
            if cls.settings.value("sql_db", False, bool):
                SqlContext.init(cls.settings, echo=echo_sql)
                cls.db = SqlLoader(SqlContext.engine, SqlContext.scoped_session).load()
            else:
                cls.db = PickleLoader().load()
        elif db_type == DbType.SQL:
            SqlContext.init(cls.settings, echo=echo_sql)
            cls.db = SqlLoader(SqlContext.engine, SqlContext.scoped_session).load()
        else:
            cls.db = PickleLoader().load()

        cls.application = application

        cls.clipboard = application.clipboard()

        cls.cube_api_client = AsyncNativeApiClient(
            host="prohunterdogkeeper.dk", db=cls.db, verify_ssl=not cls.no_ssl_verify
        )

        # # https://github.com/syrusakbary/promise/issues/57
        # promise.async_instance.disable_trampoline()

        use_disk_with_remote = cls.settings.value("allow_disk_with_local_images", False, bool)

        cls.pixmap_loader = PixmapLoader(
            image_loader=ImageClient(
                cls.settings.value("remote_image_url", "prohunterdogkeeper.dk", str),
                executor=LIFOExecutor(max_workers=16),
                imageables_executor=LIFOExecutor(max_workers=8),
                use_scryfall_when_available=True,
                image_cache_size=None,
                allow_save_to_disk=use_disk_with_remote,
                allow_load_from_disk=use_disk_with_remote,
                allow_local_fallback=cls.settings.value("allow_local_image_fallback", True, bool),
            )
            if cls.settings.value("remote_images", False, bool)
            else ImageLoader(
                printing_executor=LIFOExecutor(max_workers=16),
                imageable_executor=LIFOExecutor(max_workers=8),
                image_cache_size=None,
            ),
            image_cache_size=cls.settings.value("image_cache_size", 64, int),
        )

        cls.cardboard_names = sorted(cls.db.cardboards.keys())

        cls.search_pattern_parser = SearchParser(cls.db)
        cls.undo_group = QUndoGroup()

        cls.sort_map = CustomSortMap.empty()

    def toggle_frozen_focus(self) -> bool:
        self.focus_card_frozen = not self.focus_card_frozen
        self.focus_freeze_changed.emit(self.focus_card_frozen)
        return self.focus_card_frozen

    @classmethod
    def get_undo_stack(cls) -> QUndoStack:
        stack = QUndoStack(cls.undo_group)
        stack.setUndoLimit(64)
        return stack


Context = _Context()
