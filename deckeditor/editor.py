from __future__ import annotations

import io
import traceback

import linecache
import time
import typing
import typing as t

import sys
import random
import os
import tracemalloc

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QMainWindow, QAction, QUndoView, QMessageBox, QInputDialog, QDialog, QStatusBar
from mtgorp.db import create

from deckeditor import paths
from deckeditor.components.authentication.login import LoginDialog
from deckeditor.components.draft.view import DraftTabs
from deckeditor.components.lobbies.view import LobbiesView, CreateLobbyDialog, LobbyModelClientConnection
from deckeditor.components.views.cubeedit.graphical.cubeimagepreview import GraphicsMiniView
from deckeditor.components.views.editables.deck import DeckView
from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.models.cubes.cubescene import CubeScene
from deckeditor.notifications.frame import NotificationFrame
from deckeditor.notifications.notifyable import Notifyable
from deckeditor.serialization.deckserializer import DeckSerializer
from deckeditor.values import SUPPORTED_EXTENSIONS
from magiccube.laps.traps.trap import Trap
from magiccube.laps.traps.tree.printingtree import AllNode, AnyNode
from mtgorp.db.load import DBLoadException
from mtgorp.managejson import download
from mtgorp.managejson.update import check, update_last_updated
from mtgorp.models.serilization.strategies.jsonid import JsonId
from mtgorp.tools.parsing.exceptions import ParseException
from yeetlong.multiset import Multiset

from mtgorp.db.database import CardDatabase
from mtgorp.models.persistent.printing import Printing
from mtgorp.models.serilization.serializeable import SerializationException
from mtgorp.tools.search.pattern import Criteria, Pattern
from mtgorp.tools.search.extraction import PrintingStrategy
from mtgorp.tools.parsing.search.parse import SearchPatternParseException
from mtgorp.models.persistent.expansion import Expansion

from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.application.embargo import EmbargoApp
from deckeditor.components.cardadd.cardadder import CardAddable, CardAdder
from deckeditor.components.editables.editablestabs import EditablesTabs
# from deckeditor.components.generate.dialog import PoolGenerateable
from deckeditor.models.deck import DeckModel, Deck
from deckeditor.garbage.cardcontainers.physicalcard import PhysicalCard
# from deckeditor.notifications.frame import NotificationFrame
# from deckeditor.notifications.notifyable import Notifyable
# from deckeditor.values import DeckZoneType
from deckeditor.components.cardview.cubeableview import CubeableView
from deckeditor.context.context import Context
from deckeditor.garbage.decklistview.decklistwidget import DeckListWidget


def display_top(snapshot, key_type='lineno', limit=10):
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print("#%s: %s:%s: %.1f KiB"
              % (index, filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


# class DeckWidget(QWidget):
#     printings_changed = QtCore.pyqtSignal(DeckZoneType, CardScene)
#
#     def __init__(self, name: str, parent = None):
#         super().__init__(parent = parent)
#
#         self._name = name
#
#         self._undo_stack = UndoStack()
#
#         self._card_widgets = {
#             DeckZoneType.MAINDECK: DeckZone(DeckZoneType.MAINDECK, self._undo_stack, self),
#             DeckZoneType.SIDEBOARD: DeckZone(DeckZoneType.SIDEBOARD, self._undo_stack, self),
#             DeckZoneType.POOL: DeckZone(DeckZoneType.POOL, self._undo_stack, self)
#         }
#
#         self._zones = {
#             key: window.card_container
#             for key, window in
#             self._card_widgets.items()
#         }
#
#         self._scenes_to_deck_zone = {
#             widget.card_scene: zone
#             for zone, widget in
#             self._zones.items()
#         }  # type: t.Dict[CardScene, DeckZoneType]
#
#         for card_scene in self._scenes_to_deck_zone:
#             card_scene.cards_changed.connect(self._card_widget_changed)
#
#         for window in self._card_widgets.values():
#             window.card_container.set_zones(self._zones)
#
#         self._layout = QtWidgets.QHBoxLayout(self)
#
#         self._vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)
#
#         self._horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
#
#         self._horizontal_splitter.addWidget(self.maindeck)
#         self._horizontal_splitter.addWidget(self.sideboard)
#
#         self._vertical_splitter.addWidget(self.pool)
#         self._vertical_splitter.addWidget(self._horizontal_splitter)
#
#         self._vertical_splitter.setSizes((0, 1,))
#
#         self._layout.addWidget(
#             self._vertical_splitter
#         )
#
#         self.setLayout(
#             self._layout
#         )
#
#         self.printings_changed.connect(self._printings_changed)
#
#     def _printings_changed(self, deck_zone: DeckZoneType, card_scene: CardScene) -> None:
#         if deck_zone == DeckZoneType.POOL:
#             return
#
#         Context.deck_list_view.set_deck.emit(self.maindeck.printings, self.sideboard.printings)
#
#     def _card_widget_changed(self, card_scene: CardScene) -> None:
#         self.printings_changed.emit(self._scenes_to_deck_zone[card_scene], card_scene)
#
#     @property
#     def name(self) -> str:
#         return self._name
#
#     @property
#     def deck(self) -> Deck:
#         return Deck(
#             maindeck = self.maindeck.printings,
#             sideboard = self.sideboard.printings,
#         )
#
#     @property
#     def pool(self) -> DeckZone:
#         return self._card_widgets[DeckZoneType.POOL]
#
#     @property
#     def maindeck(self) -> DeckZone:
#         return self._card_widgets[DeckZoneType.MAINDECK]
#
#     @property
#     def sideboard(self) -> DeckZone:
#         return self._card_widgets[DeckZoneType.SIDEBOARD]
#
#     @property
#     def zones(self) -> t.Dict[DeckZoneType, DeckZone]:
#         return self._card_widgets
#
#     @property
#     def card_containers(self) -> t.Iterable[CardContainer]:
#         return (card_widget.card_container for card_widget in self._card_widgets.values())
#
#     @property
#     def undo_stack(self) -> UndoStack:
#         return self._undo_stack
#
#     def exclusive_maindeck(self):
#         self._vertical_splitter.setSizes((0, 1))
#         self._horizontal_splitter.setSizes((1, 0))
#         self.maindeck.card_container.setFocus()
#
#     def exclusive_sideboard(self):
#         self._vertical_splitter.setSizes((0, 1))
#         self._horizontal_splitter.setSizes((0, 1))
#         self.sideboard.card_container.setFocus()
#
#     def exclusive_pool(self):
#         self._vertical_splitter.setSizes((1, 0))
#         self.pool.card_container.setFocus()


# class DeckTabs(QtWidgets.QTabWidget):
#     DEFAULT_TEMPLATE = 'New Deck {}'
#
#     def __init__(self, parent: QtWidgets.QWidget = None):
#         super().__init__(parent)
#         self._new_decks = 0
#         self.setTabsClosable(True)
#
#         self.tabCloseRequested.connect(self._tab_close_requested)
#         self.currentChanged.connect(self._current_changed)
#
#     def add_deck(self, deck: DeckWidget) -> None:
#         self.addTab(deck, deck.name)
#
#     def new_deck(self) -> DeckWidget:
#         deck_widget = DeckWidget(
#             name = self.DEFAULT_TEMPLATE.format(self._new_decks),
#         )
#         self.add_deck(
#             deck_widget
#         )
#         self._new_decks += 1
#
#         return deck_widget
#
#     def _tab_close_requested(self, index: int) -> None:
#         if index == 0:
#             self.new_deck()
#
#         self.removeTab(index)
#
#     def _current_changed(self, index: int) -> None:
#         Context.deck_list_view.set_deck.emit(
#             self.currentWidget().maindeck.printings,
#             self.currentWidget().sideboard.printings,
#         )


# class _MainView(QWidget):
#
#     def __init__(self, parent: 'MainWindow'):
#         super().__init__(parent)
#
#         self._deck_tabs = DeckTabs(self)
#
#         self._deck_tabs.new_deck()
#
#         self._layout = QtWidgets.QVBoxLayout()
#
#         self._layout.addWidget(self._deck_tabs)
#
#         self.setLayout(self._layout)
#
#     @property
#     def deck_tabs(self) -> DeckTabs:
#         return self._deck_tabs
#
#     @property
#     def active_deck(self) -> DeckWidget:
#         return self._deck_tabs.currentWidget()


class MainView(QWidget):

    def __init__(self, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # cube = CubeLoader(Context.db).load()
        # import random
        # printings = list(Context.db.printings.values())
        # cube = Cube(random.sample(printings, 10 ** 1))
        # cube = Cube(
        #     (
        #         Trap(
        #             AnyNode(
        #                 (
        #                     AllNode(
        #                         (
        #                             Context.db.cardboards['Through the Breach'].from_expansion('UMA'),
        #                             Context.db.cardboards['Reach Through Mists'].from_expansion('CHK'),
        #                         )
        #                     ),
        #                     AllNode(
        #                         (
        #                             Context.db.cardboards['Birds of Paradise'].from_expansion('LEA'),
        #                             Context.db.cardboards['Lightning Bolt'].from_expansion('LEA'),
        #                             Context.db.cards['Delver of Secrets'].cardboard.printing,
        #                         )
        #                     )
        #                 )
        #             )
        #         ),
        #     )
        # )
        #
        self.deck_tabs = EditablesTabs()
        # self.deck_tabs.new_deck(DeckModel(CubeScene(StaticStackingGrid, cube)))

        layout = QtWidgets.QVBoxLayout()

        # draft_tabs = DraftTabs()
        # layout.addWidget(draft_tabs)

        layout.addWidget(self.deck_tabs)

        self.setLayout(layout)

        # self._cube_model = CubeModel(cube)
        # self._cube_list_view = CubeListView(self._cube_model, self)
        # self._second_cube_list_view = CubeListView(self._cube_model, self)
        # # self._cube_list_view = CubeListView(self._cube_model)
        # # self._second_cube_list_view = CubeListView(self._cube_model)
        # # self._cube_list_view.setModel(self._cube_model)
        # # self._second_cube_list_view.setModel(self._cube_model)
        #
        # self._shitty_button = QPushButton('ok', self)
        # self._shitty_button.clicked.connect(self._button_clicked)
        #
        # self._layout = QtWidgets.QVBoxLayout()
        #
        # _layout = QtWidgets.QHBoxLayout()
        #
        # _layout.addWidget(self._cube_list_view)
        # _layout.addWidget(self._second_cube_list_view)
        # self._layout.addLayout(_layout)
        # self._layout.addWidget(self._shitty_button)
        #
        # self.setLayout(self._layout)

    # def _button_clicked(self) -> None:
    #     self._cube_model.modify(CubeDeltaOperation({Context.db.cardboards['Abrade'].from_expansion('HOU'): 10}))


class MainWindow(QMainWindow, CardAddable, Notifyable):
    search_select = QtCore.pyqtSignal(Criteria)
    pool_generated = QtCore.pyqtSignal(Multiset)

    def __init__(self, parent = None):
        super().__init__(parent)

        self._notification_frame = NotificationFrame(self)

        self.setWindowTitle('Embargo Edit')

        self._printing_view = CubeableView(self)
        Context.focus_card_changed.connect(self._printing_view.new_cubeable)

        self._card_view_dock = QtWidgets.QDockWidget('Card View', self)
        self._card_view_dock.setObjectName('card_view_dock')
        self._card_view_dock.setWidget(self._printing_view)
        self._card_view_dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        self._card_adder = CardAdder(self, self)
        self._card_adder.add_printings.connect(self._on_add_printings)

        self._card_adder_dock = QtWidgets.QDockWidget('Card Adder', self)
        self._card_adder_dock.setObjectName('card adder dock')
        self._card_adder_dock.setWidget(self._card_adder)
        self._card_adder_dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        self._undo_view = QUndoView(Context.undo_group)

        self._undo_view_dock = QtWidgets.QDockWidget('Undo View', self)
        self._undo_view_dock.setObjectName('undo view dock')
        self._undo_view_dock.setWidget(self._undo_view)
        self._undo_view_dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        self._lobby_view = LobbiesView(
            LobbyModelClientConnection()
        )
        self._lobby_view_dock = QtWidgets.QDockWidget('Lobby View', self)
        self._lobby_view_dock.setObjectName('lobbies')
        self._lobby_view_dock.setWidget(self._lobby_view)
        self._lobby_view_dock.setAllowedAreas(
            QtCore.Qt.RightDockWidgetArea
            | QtCore.Qt.LeftDockWidgetArea
            | QtCore.Qt.BottomDockWidgetArea
        )

        self._cube_view_minimap = GraphicsMiniView()
        Context.focus_scene_changed.connect(lambda scene: self._cube_view_minimap.set_scene(scene))

        self._cube_view_minimap_dock = QtWidgets.QDockWidget('Minimap', self)
        self._cube_view_minimap_dock.setObjectName('minimap')
        self._cube_view_minimap_dock.setWidget(self._cube_view_minimap)
        self._cube_view_minimap_dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        # self._deck_list_widget = DeckListWidget(self)
        # self._deck_list_widget.set_deck.emit((), ())
        # Context.deck_list_view = self._deck_list_widget
        #
        # self._deck_list_docker = QtWidgets.QDockWidget('Deck List', self)
        # self._deck_list_docker.setObjectName('deck_list_dock')
        # self._deck_list_docker.setWidget(self._deck_list_widget)
        # self._deck_list_docker.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._card_adder_dock)
        # self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._deck_list_docker)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._card_view_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._undo_view_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._lobby_view_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._cube_view_minimap_dock)

        self._card_adder_dock.hide()
        # self._deck_list_docker.hide()
        # self._card_view_dock.hide()
        self._undo_view_dock.hide()

        self._main_view = MainView(self)

        self.setCentralWidget(self._main_view)

        menu_bar = self.menuBar()

        all_menus = {
            menu_bar.addMenu('File'): (
                ('Exit', 'Ctrl+Q', self.close),
                ('New Deck', 'Ctrl+N', self._new_deck),
                ('Open Deck', 'Ctrl+O', self._load),
                # ('Load Pool', 'Ctrl+P', self.load_pool),
                ('Save Deck', 'Ctrl+S', self._save_as),
                # ('Save pool', 'Ctrl+l', self.save_pool),
                ('Close Deck', 'Ctrl+W', self._close_deck),

            ),
            menu_bar.addMenu('Edit'): (
                ('Undo', 'Ctrl+Z', self._undo),
                ('Redo', 'Ctrl+Shift+Z', self._redo),
            ),
            menu_bar.addMenu('Deck'): (
                # ('Maindeck', 'Ctrl+1', lambda: self._focus_deck_zone(DeckZoneType.MAINDECK)),
                # ('Sideboard', 'Ctrl+2', lambda: self._focus_deck_zone(DeckZoneType.SIDEBOARD)),
                # ('Pool', 'Ctrl+3', lambda: self._focus_deck_zone(DeckZoneType.POOL)),
                # ('Exclusive Maindeck', 'Alt+Ctrl+1', self._exclusive_maindeck),
                # ('Exclusive Sideboard', 'Alt+Ctrl+2', self._exclusive_sideboard),
                # ('Exclusive Pool', 'Alt+Ctrl+3', self._exclusive_pool),
            ),
            menu_bar.addMenu('Generate'): (
                # ('Sealed pool', 'Ctrl+G', self._generate_pool),
                # ('Cube Pools', 'Ctrl+C', self.generate_cube_pools),
            ),
            menu_bar.addMenu('Add'): (
                # ('Test Add', 'Ctrl+W', self._test_add),
                ('Add cards', 'Ctrl+F', self._add_cards),
            ),
            menu_bar.addMenu('Select'): (
                # ('All', 'Ctrl+A', self._select_all),
                # ('Clear Selection', 'Ctrl+D', self._clear_selection),
                # ('Select Matching', 'Ctrl+E', self._search_select),
            ),
            menu_bar.addMenu('View'): (
                ('Card View', 'Meta+1', lambda: self._toggle_dock_view(self._card_view_dock)),
                ('Card Adder', 'Meta+2', lambda: self._toggle_dock_view(self._card_adder_dock)),
                # ('Deck List View', 'Meta+3', lambda: self._toggle_dock_view(self._deck_list_docker)),
                ('Lobbies', 'Meta+4', lambda: self._toggle_dock_view(self._lobby_view_dock)),
                ('Undo', 'Meta+5', lambda: self._toggle_dock_view(self._undo_view_dock)),
                ('Minimap', 'Meta+6', lambda: self._toggle_dock_view(self._cube_view_minimap_dock)),
            ),
            menu_bar.addMenu('Test'): (
                ('Test', 'Ctrl+T', self._test),
            ),
            menu_bar.addMenu('Connect'): (
                ('Login', 'Ctrl+L', self._login),
            ),
            menu_bar.addMenu('DB'): (
            ),
        }

        for menu in all_menus:
            for name, shortcut, action in all_menus[menu]:
                _action = QAction(name, self)
                if shortcut:
                    _action.setShortcut(shortcut)
                _action.triggered.connect(action)
                menu.addAction(_action)

        self._printings = None

        # self._last_focused_card_container = None  # type: # t.Optional[CardContainer]

        self._reset_dock_width = 500
        self._reset_dock_height = 1200

        self.search_select.connect(self._search_selected)
        # self.pool_generated.connect(self._pool_generated)

        self._status_bar = QStatusBar()

        self.setStatusBar(self._status_bar)

        self._status_bar.showMessage('LMAO LETS GO BOIS')

        self._load_state()

    def _on_add_printings(self, delta_operation: CubeDeltaOperation):
        tab = self._main_view.deck_tabs.currentWidget()
        if isinstance(tab, DeckView):
            tab.undo_stack.push(
                tab.deck_model.maindeck.get_cube_modification(delta_operation)
            )

    def _login(self):
        dialog = LoginDialog(self)
        dialog.exec()

    @staticmethod
    def _toggle_dock_view(dock: QtWidgets.QDockWidget):
        dock.setVisible(not dock.isVisible())

    def _new_deck(self) -> None:
        self._main_view.deck_tabs.setCurrentWidget(
            self._main_view.deck_tabs.new_deck(
                DeckModel()
            )
        )

    def _close_deck(self) -> None:
        self._main_view.deck_tabs.tabCloseRequested.emit(
            self._main_view.deck_tabs.currentIndex()
        )

    def _undo(self):
        Context.undo_group.undo()

    def _redo(self):
        Context.undo_group.redo()

    def notify(self, message: str) -> None:
        self._notification_frame.notify(message)

    # def _focus_deck_zone(self, zone: DeckZoneType):
    #     self._main_view.active_deck.zones[zone].card_container.setFocus()

    def _exclusive_maindeck(self):
        self._main_view.active_deck.exclusive_maindeck()

    def _exclusive_sideboard(self):
        self._main_view.active_deck.exclusive_sideboard()

    def _exclusive_pool(self):
        self._main_view.active_deck.exclusive_pool()

    def _select_all(self):
        if (
            self._main_view.active_deck is None
            or not self._last_focused_card_container in self._main_view.active_deck.card_containers
        ):
            return

        self._last_focused_card_container.cube_scene.select_all()

    def _clear_selection(self):
        if (
            not self._main_view.active_deck
            or not self._last_focused_card_container in self._main_view.active_deck.card_containers
        ):
            return

        self._last_focused_card_container.cube_scene.clear_selection()

    def _search_selected(self, criteria: Criteria):
        if (
            not self._main_view.active_deck
            or not self._last_focused_card_container in self._main_view.active_deck.card_containers
        ):
            return

        pattern = Pattern(criteria, PrintingStrategy)

        self._last_focused_card_container.cube_scene.add_select_if(lambda card: pattern.match(card.cubeable))

    def _add_cards(self):
        self._card_adder_dock.activateWindow()
        if self._card_adder_dock.isHidden():
            self._card_adder_dock.show()

            if self._card_adder_dock.width() < self._reset_dock_width:
                self.resizeDocks([self._card_adder_dock], [self._reset_dock_width], QtCore.Qt.Horizontal)

            if self._card_adder_dock.height() < self._reset_dock_height:
                self.resizeDocks([self._card_adder_dock], [self._reset_dock_height], QtCore.Qt.Vertical)

        self._card_adder.query_edit.setFocus()

    def _test(self):
        raise Exception('test')
        # display_top(tracemalloc.take_snapshot())
        # print(self._main_view.active_deck, type(self._main_view.active_deck), dir(self._main_view.active_deck))
        # print(self._main_view.active_deck.deck)

    def resizeEvent(self, resize_event: QtGui.QResizeEvent):
        if hasattr(self, '_notification_frame'):
            self._notification_frame.stack_notifications()

    # def focus_changed(self, old_widget: QtWidgets.QWidget, new_widget: QtWidgets.QWidget):
    #     if isinstance(new_widget, CardContainer):
    #         self._last_focused_card_container = new_widget

    # def _add_card(self, db: CardDatabase):
    #     if self._printings is None:
    #         self._printings = list(db.printings.values())
    #
    #     sampled = random.sample(self._printings, 9) + [
    #         db.cardboards['Huntmaster of the Fells // Ravager of the Fells'].printing]
    #
    #     self._main_view.active_deck.undo_stack.push(
    #         AddPrintings(
    #             (
    #                 self._last_focused_card_container
    #                 if (
    #                     self._last_focused_card_container is not None
    #                     and self._last_focused_card_container in
    #                     (
    #                         card_window.card_container
    #                         for card_window in
    #                         self._main_view.active_deck.zones.values()
    #                     )
    #                 ) else
    #                 self._main_view.active_deck.maindeck.card_container
    #             ).scene(),
    #             sampled,
    #             QtCore.QPointF(0, 0),
    #         )
    #     )

    # def _test_add(self):
    #     self._add_card(Context.db)

    # def add_printings(self, target: DeckZoneType, printings: t.Iterable[Printing]):
    #     self._main_view.active_deck.undo_stack.push(
    #         AddPrintings(
    #             self._main_view.active_deck.zones[target].card_container.scene(),
    #             printings,
    #         )
    #     )

    def generate_cube_pools(self):
        pass

    def _load(self):
        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setNameFilter(SUPPORTED_EXTENSIONS)
        dialog.setViewMode(QtWidgets.QFileDialog.List)

        if not dialog.exec_():
            return

        file_names = dialog.selectedFiles()

        if not file_names:
            return

        file_path = file_names[0]

        self._main_view.deck_tabs.open_file(file_path)

    def _save(self):
        pass

    def _save_as(self):
        self._main_view.deck_tabs.save_tab()

    # def _pool_generated(self, key: Multiset[Expansion]):
    #     deck_widget = DeckWidget('Generated Pool')
    #
    #     self._main_view.deck_tabs.add_deck(deck_widget)
    #
    #     self._main_view.deck_tabs.setCurrentWidget(deck_widget)
    #
    #     deck_widget.undo_stack.push(
    #         AddPrintings(
    #             deck_widget.zones[DeckZoneType.POOL].card_container.card_scene,
    #             (printing for expansion in key for printing in expansion.generate_booster()),
    #         )
    #     )
    #
    # def _generate_pool(self):
    #     dialog = GeneratePoolDialog(self, self)
    #     dialog.exec()

    def _save_state(self):
        Context.settings.setValue('geometry', self.saveGeometry())
        Context.settings.setValue('window_state', self.saveState(0))
        self._main_view.deck_tabs.save()
        # Context.settings.beginGroup('main_window')
        # Context.settings.setValue('size', self.size())
        # Context.settings.setValue('position', self.pos())
        # Context.settings.setValue('state', self.saveState(0))
        # Context.settings.endGroup()

    def _load_state(self):
        geometry = Context.settings.value('geometry', None)
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = Context.settings.value('window_state')
        if state is not None:
            self.restoreState(state, 0)
        self._main_view.deck_tabs.load()
        # Context.settings.beginGroup('main_window')
        #
        # saved_size = Context.settings.value('size', None)
        # if saved_size is not None:
        #     self.resize(saved_size)
        #
        # saved_position = Context.settings.value('position', None)
        # if saved_position is not None:
        #     self.move(saved_position)
        #
        # saved_state = Context.settings.value('state', None)
        # if saved_state is not None:
        #     self.restoreState(saved_state, 0)
        #
        # Context.settings.endGroup()

    def closeEvent(self, close_event):
        self._save_state()
        super().closeEvent(close_event)




def _get_exception_hook(main_window: t.Optional[MainWindow] = None) -> t.Callable[[t.Any, t.Any, t.Any], None]:
    def exception_hook(exception_type, exception_value, _traceback):
        separator = '-' * 80
        time_string = time.strftime("%Y-%m-%d, %H:%M:%S")

        traceback_info_file = io.StringIO()
        traceback.print_tb(_traceback, None, traceback_info_file)
        traceback_info_file.seek(0)
        traceback_info = traceback_info_file.read()

        errmsg = '{} {}'.format(
            str(exception_type),
            str(exception_value),
        )

        msg = '\n'.join(
            (separator, time_string, traceback_info, errmsg, '\n')
        )

        try:
            if not os.path.exists(paths.APP_DATA_PATH):
                os.makedirs(paths.APP_DATA_PATH)

            with open(paths.LOGS_PATH, 'a') as log_file:
                log_file.write(msg)
        except IOError:
            pass

        print(traceback_info)
        print(errmsg)

        errorbox = QMessageBox()
        errorbox.setText(
            'OH NO :O\n{}\n{}'.format(
                traceback_info,
                errmsg,
            )
        )
        errorbox.exec_()
        if main_window is not None:
            main_window.close()

    return exception_hook


class MtgOrpDialog(QDialog):

    def __init__(self):
        super().__init__()
        self._info_label = QtWidgets.QLabel('Can\'t load db, gotta rebuild')

        self._log_value = ''
        self._log_view = QtWidgets.QTextEdit()
        self._log_view.setReadOnly(True)

        self._run_button = QtWidgets.QPushButton('Download and generate')
        self._run_button.clicked.connect(self._download_and_generate)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._info_label)
        layout.addWidget(self._log_view)
        layout.addWidget(self._run_button)

    def _log(self, text: str) -> None:
        self._log_value += text + '\n'
        self._log_view.setText(self._log_value)
        self._log_view.repaint()

    def _download_and_generate(self):
        self._run_button.setDisabled(True)
        self._log('Checking db')
        last_updates = check()
        if last_updates is not None:
            self._log('New magic json')
            download.re_download()
            self._log('New magic json downloaded')
            create.update_database()
            self._log('Database updated')
            update_last_updated(last_updates)
        else:
            self._log('Magic db up to date')
        self.accept()


def run():
    app = EmbargoApp(sys.argv)

    sys.excepthook = _get_exception_hook()

    app.setQuitOnLastWindowClosed(True)

    try:
        Context.init()
    except DBLoadException:
        if not MtgOrpDialog().exec_() == QDialog.Accepted:
            return
        Context.init()

    main_window = MainWindow()

    sys.excepthook = _get_exception_hook(main_window)

    # app.aboutToQuit.connect(Context.settings.)

    main_window.showMaximized()

    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
