import typing as t

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import QUndoGroup, QGraphicsScene, QApplication, QUndoStack

from cubeclient.endpoints import NativeApiClient
from mtgorp.db.database import CardDatabase
from mtgorp.db.load import Loader
from mtgorp.models.interfaces import Cardboard
from mtgorp.tools.parsing.search.parse import SearchParser

from mtgimg.load import Loader as ImageLoader

from cubeclient.models import ApiClient

from mtgqt.pixmapload.pixmaploader import PixmapLoader


class _Context(QObject):
    settings: QtCore.QSettings
    pixmap_loader: PixmapLoader

    db: CardDatabase
    basics: t.List[Cardboard]

    cardboard_names: t.List[str]
    search_pattern_parser: SearchParser
    undo_group: QUndoGroup
    clipboard : QClipboard

    host: str
    username: str
    token_changed = pyqtSignal(str)

    cube_api_client: ApiClient

    notification_message = pyqtSignal(str)

    focus_card_changed = pyqtSignal(object)
    focus_scene_changed = pyqtSignal(QGraphicsScene)

    draft_started = pyqtSignal(object)

    new_pool = pyqtSignal(object)

    @classmethod
    def init(cls, application: QApplication) -> None:
        cls.db = Loader.load()
        cls.basics = [
            cls.db.cardboards[name]
            for name in
            ('Plains', 'Island', 'Swamp', 'Mountain', 'Forest')
        ]

        cls.clipboard = application.clipboard()

        cls.settings = QtCore.QSettings('lost-world', 'Embargo Edit')

        cls.host = Context.settings.value('host_name', 'localhost:7000')
        cls.username = Context.settings.value('username', 'root')
        cls.cube_api_client = NativeApiClient(host = cls.host, db = cls.db)

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

    @classmethod
    def get_undo_stack(cls) -> QUndoStack:
        stack = QUndoStack(cls.undo_group)
        stack.setUndoLimit(64)
        return stack


Context = _Context()
