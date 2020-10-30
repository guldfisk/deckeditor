import threading
import typing as t
from enum import Enum

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import QUndoGroup, QGraphicsScene, QApplication, QUndoStack, QMainWindow

from promise import promise

from mtgorp.db.database import CardDatabase
from mtgorp.db.load import PickleLoader, SqlLoader
from mtgorp.tools.parsing.search.parse import SearchParser

from mtgimg.load import Loader as ImageLoader

from magiccube.collections.cube import Cube
from magiccube.collections.infinites import Infinites

from cubeclient.endpoints import AsyncNativeApiClient
from cubeclient.images import ImageClient

from mtgqt.pixmapload.pixmaploader import PixmapLoader

from deckeditor.components.editables.editor import Editor
from deckeditor.components.cardview.focuscard import CubeableFocusEvent
from deckeditor.sorting.custom import CustomSortMap
from deckeditor.context.sql import SqlContext


class DbType(Enum):
    DEFAULT = 'default'
    PICKLE = 'pickle'
    SQL = 'sql'


class _Context(QObject):
    debug: bool = False

    settings: QtCore.QSettings
    pixmap_loader: PixmapLoader

    db: CardDatabase

    compiled: bool

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

    focus_card_changed = pyqtSignal(CubeableFocusEvent)
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
    ) -> None:
        cls.debug = debug

        cls.compiled = compiled

        cls.settings = QtCore.QSettings('lost-world', 'Embargo Edit')

        if db_type == DbType.DEFAULT:
            if cls.settings.value('sql_db', False, bool):
                SqlContext.init(cls.settings)
                cls.db = SqlLoader(SqlContext.engine, SqlContext.scoped_session).load()
            else:
                cls.db = PickleLoader().load()
        elif db_type == DbType.SQL:
            SqlContext.init(cls.settings)
            cls.db = SqlLoader(SqlContext.engine, SqlContext.scoped_session).load()
        else:
            cls.db = PickleLoader().load()

        cls.application = application

        cls.clipboard = application.clipboard()

        cls.cube_api_client = AsyncNativeApiClient(host = 'prohunterdogkeeper.dk', db = cls.db)

        # https://github.com/syrusakbary/promise/issues/57
        promise.async_instance.disable_trampoline()

        cls.pixmap_loader = PixmapLoader(
            image_loader = ImageClient(
                cls.settings.value('remote_image_url', 'prohunterdogkeeper.dk', str),
                executor = 16,
                imageables_executor = 8,
                use_scryfall_when_available = True,
                image_cache_size = None,
                allow_local_fallback = cls.settings.value('allow_local_image_fallback', True, bool),
            ) if cls.settings.value('remote_images', False, bool) else
            ImageLoader(
                printing_executor = 16,
                imageable_executor = 8,
                image_cache_size = None,
            ),
        )

        cls.cardboard_names = sorted(cls.db.cardboards.keys())

        cls.search_pattern_parser = SearchParser(cls.db)
        cls.undo_group = QUndoGroup()

        cls.sort_map = CustomSortMap.empty()

    @classmethod
    def get_undo_stack(cls) -> QUndoStack:
        stack = QUndoStack(cls.undo_group)
        stack.setUndoLimit(64)
        return stack


Context = _Context()
