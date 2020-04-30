import typing as t

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import QUndoGroup, QGraphicsScene, QApplication, QUndoStack, QMainWindow

from promise import promise

from deckeditor.components.cardview.focuscard import CubeableFocusEvent
from deckeditor.sorting.custom import CustomSortMap
from mtgorp.db.database import CardDatabase
from mtgorp.db.load import Loader
from mtgorp.models.interfaces import Cardboard
from mtgorp.tools.parsing.search.parse import SearchParser

from mtgimg.load import Loader as ImageLoader

from cubeclient.models import ApiClient, AsyncClient
from cubeclient.endpoints import NativeApiClient, AsyncNativeApiClient

from mtgqt.pixmapload.pixmaploader import PixmapLoader

from deckeditor.components.editables.editor import Editor


class _Context(QObject):
    settings: QtCore.QSettings
    pixmap_loader: PixmapLoader

    db: CardDatabase
    basics: t.List[Cardboard]

    cardboard_names: t.List[str]
    search_pattern_parser: SearchParser
    undo_group: QUndoGroup
    clipboard: QClipboard
    main_window: QMainWindow
    application: QApplication

    editor: Editor

    host: str
    username: str
    token_changed = pyqtSignal(str)

    cube_api_client: AsyncClient

    notification_message = pyqtSignal(str)
    status_message = pyqtSignal(str, int)

    focus_card_changed = pyqtSignal(CubeableFocusEvent)
    focus_scene_changed = pyqtSignal(QGraphicsScene)

    draft_started = pyqtSignal(object)
    sealed_started = pyqtSignal(int)

    new_pool = pyqtSignal(object, str)

    saved_drafts: t.Mapping[str, t.Any]

    sort_map: CustomSortMap

    @classmethod
    def init(cls, application: QApplication) -> None:
        cls.db = Loader.load()
        cls.basics = [
            cls.db.cardboards[name]
            for name in
            ('Plains', 'Island', 'Swamp', 'Mountain', 'Forest')
        ]

        cls.application = application

        cls.clipboard = application.clipboard()

        cls.settings = QtCore.QSettings('lost-world', 'Embargo Edit')

        cls.host = Context.settings.value('host_name', 'localhost:7000')
        cls.username = Context.settings.value('username', 'root')
        cls.cube_api_client = AsyncNativeApiClient(host = cls.host, db = cls.db)

        # https://github.com/syrusakbary/promise/issues/57
        promise.async_instance.disable_trampoline()

        cls.pixmap_loader = PixmapLoader(
            pixmap_executor = 30,
            image_loader = ImageLoader(
                printing_executor = 20,
                imageable_executor = 10,
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
