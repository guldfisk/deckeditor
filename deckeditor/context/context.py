import typing as t

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QUndoGroup

from mtgorp.db.database import CardDatabase
from mtgorp.db.load import Loader, DBLoadException
from mtgorp.managejson.update import update
from mtgorp.models.serilization.strategies.jsonid import JsonId
from mtgorp.tools.parsing.search.parse import SearchParser

from mtgqt.pixmapload.pixmaploader import PixmapLoader

from deckeditor.context.serialize import SoftSerialization
from deckeditor.garbage.decklistview.decklistwidget import DeckListWidget


class _Context(QObject):

    settings: QtCore.QSettings
    pixmap_loader: PixmapLoader
    db: CardDatabase
    soft_serialization: SoftSerialization
    search_pattern_parser: SearchParser
    deck_list_view: DeckListWidget
    undo_group: QUndoGroup

    host: str
    token: str
    username: str
    token_changed = pyqtSignal(str)

    focus_card_changed = pyqtSignal(object)

    @classmethod
    def init(cls) -> None:
        cls.settings = QtCore.QSettings('lost-world', 'Embargo Edit')

        cls.token = ''
        cls.host = Context.settings.value('host_name', 'localhost:7000')
        cls.username = Context.settings.value('username', 'root')

        cls.pixmap_loader = PixmapLoader(
            pixmap_executor = 30,
            printing_executor = 30,
            imageable_executor = 30,
        )

        try:
            cls.db = Loader.load()
        except DBLoadException:
            update()
            cls.db = Loader.load()

        json_id = JsonId(cls.db)

        cls.soft_serialization = SoftSerialization(
            [json_id],
            {
                'emb': json_id,
            },
        )

        cls.search_pattern_parser = SearchParser(cls.db)
        cls.undo_group = QUndoGroup()


Context = _Context()
