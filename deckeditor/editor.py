from __future__ import annotations

import io
import logging
import os
import pickle
import sys
import time
import traceback
import argparse
import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QMainWindow, QAction, QUndoView, QMessageBox, QDialog

from deckeditor.store import models, engine
from deckeditor.store.models import GameTypeOptions
from yeetlong.multiset import Multiset

from mtgorp.db.load import DBLoadException

from magiccube.collections.delta import CubeDeltaOperation

from deckeditor import paths
from deckeditor.application.embargo import EmbargoApp
from deckeditor.components.authentication.login import LoginDialog
from deckeditor.components.cardadd.cardadder import CardAddable, CardAdder
from deckeditor.components.cardview.cubeableview import CubeableView
from deckeditor.components.editables.editablestabs import FileOpenException, EditablesTabs, FileSaveException
from deckeditor.components.lobbies.view import LobbiesView, LobbyModelClientConnection
from deckeditor.components.views.cubeedit.graphical.cubeimagepreview import GraphicsMiniView
from deckeditor.components.views.editables.deck import DeckView
from deckeditor.context.context import Context
from deckeditor.models.deck import DeckModel, Deck, TabModel, Pool
from deckeditor.notifications.frame import NotificationFrame
from deckeditor.values import SUPPORTED_EXTENSIONS
from deckeditor.authentication.login import LOGIN_CONTROLLER
from deckeditor.components.db.info import DBInfoDialog
from deckeditor.components.db.update import DBUpdateDialog
from deckeditor.components.draft.view import DraftView
from deckeditor.components.help.about import AboutDialog
from deckeditor.components.sealed.view import LimitedSessionsView
from deckeditor.components.settings.dialog import SettingsDialog
from deckeditor.components.views.editables.pool import PoolView
from deckeditor.serialization.tabmodelserializer import init_deck_serializers
from deckeditor.server.client import EmbargoClient
from deckeditor.server.server import EmbargoServer
from deckeditor.sorting.custom import CustomSortMap
from deckeditor.utils.version import version_formatted


class MainView(QWidget):

    def __init__(self, parent: t.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(3, 0, 3, 0)

        self.editables_tabs = EditablesTabs()

        Context.editor = self.editables_tabs

        layout.addWidget(self.editables_tabs)

        self.setLayout(layout)


class Dock(QtWidgets.QDockWidget):

    def __init__(
        self,
        name: str,
        object_name: str,
        parent: QMainWindow,
        content: QtWidgets.QWidget,
        allowed_areas: int = QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea,
        wants_focus: bool = True,
    ):
        super().__init__(name, parent)
        self.setWidget(content)
        self.setFocusProxy(content)
        self.setObjectName(object_name)
        self.setAllowedAreas(allowed_areas)

        self._wants_focus = wants_focus

    @property
    def wants_focus(self) -> bool:
        return self._wants_focus


class MainWindow(QMainWindow, CardAddable):
    pool_generated = QtCore.pyqtSignal(Multiset)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.setWindowIcon(QtGui.QIcon(paths.ICON_PATH))
        if Context.settings.value('frameless', True, bool):
            self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self._notification_frame = NotificationFrame(self)

        self.setWindowTitle('Embargo Edit')

        self.layout().setContentsMargins(0, 0, 0, 0)

        self._printing_view = CubeableView(self)
        Context.focus_card_changed.connect(self._printing_view.new_cubeable)

        self._login_status_label = QtWidgets.QLabel('')
        LOGIN_CONTROLLER.login_success.connect(lambda u, h: self._login_status_label.setText(f'{u.username}@{h}'))
        LOGIN_CONTROLLER.login_failed.connect(lambda e: self._login_status_label.setText(''))
        LOGIN_CONTROLLER.login_terminated.connect(lambda: self._login_status_label.setText(''))
        LOGIN_CONTROLLER.login_pending.connect(lambda u, h: self._login_status_label.setText(f'logging in @ {h}'))

        self.statusBar().setContentsMargins(10, 0, 10, 0)
        self.statusBar().addPermanentWidget(self._login_status_label)
        Context.status_message.connect(lambda m, t: self.statusBar().showMessage(m, t))

        self._card_view_dock = Dock('Card View', 'card_view_dock', self, self._printing_view, wants_focus = False)

        self._card_adder = CardAdder(self)
        self._card_adder.add_printings.connect(self._on_add_printings)

        self._card_adder_dock = Dock('Card Adder', 'card adder dock', self, self._card_adder)

        self._undo_view = QUndoView(Context.undo_group)

        self._undo_view_dock = Dock('Undo View', 'undo view dock', self, self._undo_view)

        self._lobby_view = LobbiesView(
            LobbyModelClientConnection()
        )
        self._lobby_view_dock = Dock(
            'Lobby View',
            'lobbies',
            self,
            self._lobby_view,
            allowed_areas = QtCore.Qt.RightDockWidgetArea
                            | QtCore.Qt.LeftDockWidgetArea
                            | QtCore.Qt.BottomDockWidgetArea,
        )

        self._cube_view_minimap = GraphicsMiniView()
        Context.focus_scene_changed.connect(lambda scene: self._cube_view_minimap.set_scene(scene))

        self._cube_view_minimap_dock = Dock('Minimap', 'minimap', self, self._cube_view_minimap, wants_focus = False)

        self._limited_sessions_view = LimitedSessionsView()

        self._limited_sessions_dock = Dock('Limited', 'Limited', self, self._limited_sessions_view)

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
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._limited_sessions_dock)

        self._card_view_dock.hide()
        self._card_adder_dock.hide()
        self._undo_view_dock.hide()
        self._lobby_view_dock.hide()
        self._cube_view_minimap_dock.hide()
        self._limited_sessions_dock.hide()

        self._main_view = MainView(self)

        self.setCentralWidget(self._main_view)

        menu_bar = self.menuBar()

        all_menus = {
            menu_bar.addMenu('File'): (
                ('New Deck', 'Ctrl+N', self._new_deck),
                ('Open Deck', 'Ctrl+O', lambda: self.open(Deck)),
                ('Open Pool', 'Ctrl+P', lambda: self.open(Pool)),
                ('Save', 'Ctrl+S', self._save),
                ('Save As', 'Ctrl+Shift+S', self._save_as),
                ('Export Deck', 'Ctrl+Shift+E', self._export_deck),
                ('Close Tab', 'Ctrl+W', self._close_tab),
                'line',
                ('Exit', 'Ctrl+Q', self.close),

            ),
            menu_bar.addMenu('Edit'): (
                ('Undo', 'Ctrl+Z', Context.undo_group.undo),
                ('Redo', 'Ctrl+Shift+Z', Context.undo_group.redo),
                'line',
                ('Add cards', 'Ctrl+F', self._add_cards),
            ),
            # menu_bar.addMenu('Generate'): (
            #     # ('Sealed pool', 'Ctrl+G', self._generate_pool),
            #     # ('Cube Pools', 'Ctrl+C', self.generate_cube_pools),
            # ),
            menu_bar.addMenu('View'): (
                ('Card View', 'Meta+1', lambda: self._toggle_dock_view(self._card_view_dock)),
                ('Card Adder', 'Meta+2', lambda: self._toggle_dock_view(self._card_adder_dock)),
                ('Limited', 'Meta+3', lambda: self._toggle_dock_view(self._limited_sessions_dock)),
                ('Lobbies', 'Meta+4', lambda: self._toggle_dock_view(self._lobby_view_dock)),
                ('Undo', 'Meta+5', lambda: self._toggle_dock_view(self._undo_view_dock)),
                ('Minimap', 'Meta+6', lambda: self._toggle_dock_view(self._cube_view_minimap_dock)),
            ),
            # menu_bar.addMenu('Test'): (
            #     ('Test', 'Ctrl+T', restart),
            # ),
            menu_bar.addMenu('Connect'): (
                ('Login', 'Ctrl+L', LoginDialog(self).exec_),
                ('Logout', None, LOGIN_CONTROLLER.log_out),
            ),
            menu_bar.addMenu('Preferences'): (
                ('Settings', 'Ctrl+Alt+S', lambda: SettingsDialog.get().exec_()),
            ),
            menu_bar.addMenu('DB'): (
                ('Info', None, lambda: DBInfoDialog().exec_()),
                ('Update', None, lambda: DBUpdateDialog().exec_()),
                ('Validate', None, lambda: LOGIN_CONTROLLER.validate(True)),
            ),
            menu_bar.addMenu('Help'): (
                ('About', None, lambda: AboutDialog().exec_()),
            ),
        }

        for menu in all_menus:
            for line in all_menus[menu]:
                if line == 'line':
                    menu.addSeparator()
                else:
                    name, shortcut, action = line
                    _action = QAction(name, self)
                    if shortcut:
                        _action.setShortcut(shortcut)
                    _action.triggered.connect(action)
                    menu.addAction(_action)

        self._reset_dock_width = 500
        self._reset_dock_height = 1200

        self.resizeDocks([self._card_view_dock], [self._reset_dock_width], QtCore.Qt.Horizontal)

        Context.notification_message.connect(self._notification_frame.notify)
        Context.draft_started.connect(self._on_draft_started)

        self._load_state()

    def _on_draft_started(self, key: str) -> None:
        if Context.settings.value('hide_lobbies_on_new_draft', True, bool):
            self._lobby_view_dock.hide()

    @property
    def login_status_label(self) -> QtWidgets.QLabel:
        return self._login_status_label

    def _on_add_printings(self, delta_operation: CubeDeltaOperation):
        tab = self._main_view.editables_tabs.currentWidget()
        if isinstance(tab, DeckView):
            tab.undo_stack.push(
                tab.deck_model.maindeck.get_cube_modification(delta_operation)
            )
        elif isinstance(tab, PoolView):
            tab.undo_stack.push(
                tab.pool_model.maindeck.get_cube_modification(delta_operation)
            )
        elif isinstance(tab, DraftView):
            tab.undo_stack.push(
                tab.pool_model.maindeck.get_cube_modification(delta_operation)
            )

    def _toggle_dock_view(self, dock: Dock) -> None:
        if dock.wants_focus:
            if dock.hasFocus():
                dock.setVisible(False)
            else:
                dock.setVisible(True)
                dock.setFocus()
        else:
            dock.setVisible(not dock.isVisible())

    def _new_deck(self) -> None:
        self._main_view.editables_tabs.setCurrentWidget(
            self._main_view.editables_tabs.new_deck(
                DeckModel()
            )
        )

    def _close_tab(self) -> None:
        self._main_view.editables_tabs.tabCloseRequested.emit(
            self._main_view.editables_tabs.currentIndex()
        )

    def _add_cards(self):
        self._card_adder_dock.activateWindow()
        if self._card_adder_dock.isHidden():
            self._card_adder_dock.show()

            if self._card_adder_dock.width() < self._reset_dock_width:
                self.resizeDocks([self._card_adder_dock], [self._reset_dock_width], QtCore.Qt.Horizontal)

            if self._card_adder_dock.height() < self._reset_dock_height:
                self.resizeDocks([self._card_adder_dock], [self._reset_dock_height], QtCore.Qt.Vertical)

        self._card_adder.query_edit.setFocus()

    def resizeEvent(self, resize_event: QtGui.QResizeEvent):
        if hasattr(self, '_notification_frame'):
            self._notification_frame.stack_notifications()

    def generate_cube_pools(self):
        pass

    def open(self, target: t.Type[TabModel] = Deck):
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

        try:
            self._main_view.editables_tabs.open_file(file_path, target)
        except FileOpenException as e:
            Context.notification_message.emit('Corrupt file or wrong inferred type.\n{}'.format(e))

    def _save(self):
        try:
            self._main_view.editables_tabs.save_tab()
        except FileSaveException:
            Context.notification_message.emit('Invalid extension')

    def _save_as(self):
        try:
            self._main_view.editables_tabs.save_tab_as()
        except FileSaveException:
            Context.notification_message.emit('Invalid extension')

    def _export_deck(self):
        try:
            self._main_view.editables_tabs.export_deck()
        except FileSaveException:
            Context.notification_message.emit('Invalid extension')

    def save_state(self):
        Context.settings.setValue('geometry', self.saveGeometry())
        Context.settings.setValue('window_state', self.saveState(0))
        self._main_view.editables_tabs.save_session()
        Context.sort_map.save()

    def _load_state(self):
        geometry = Context.settings.value('geometry', None)
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = Context.settings.value('window_state')
        if state is not None:
            self.restoreState(state, 0)
        self._main_view.editables_tabs.load_session()
        try:
            Context.sort_map = CustomSortMap.load()
        except (pickle.UnpicklingError, EOFError):
            Context.notification_message.emit('Failed loading custom sort map')
            return CustomSortMap.empty()

    def closeEvent(self, close_event):
        self.save_state()
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

        logging.error(traceback_info)
        logging.error(errmsg)

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


def run():
    sys.excepthook = _get_exception_hook()

    arg_parser = argparse.ArgumentParser(description = 'Edit decks')
    arg_parser.add_argument(
        '-v', '--version',
        action = 'store_true',
        help = 'show version',
    )
    arg_parser.add_argument(
        '-m', '--multi-instance',
        action = 'store_true',
        help = 'allow running in parallel with other instances of Embargo Edit',
    )
    arg_parser.add_argument(
        '-d', '--debug',
        action = 'store_true',
        help = 'debug mode',
    )
    arg_parser.add_argument(
        '-n', '--no-server',
        action = 'store_true',
        help = 'dont start server',
    )
    arg_parser.add_argument(
        '--port',
        metavar = 'P',
        type = int,
        nargs = '?',
        default = 7777,
        help = 'server port',
    )
    arg_parser.add_argument(
        '--host',
        metavar = 'H',
        type = str,
        nargs = '?',
        default = 'localhost',
        help = 'server host',
    )
    arg_parser.add_argument('files', metavar = 'F', type = str, nargs = '*', help = 'paths of files to open')

    args = arg_parser.parse_args()

    logging.basicConfig(
        format = '%(levelname)s %(message)s',
        level = logging.DEBUG if args.debug else logging.INFO,
    )

    if args.version:
        print(version_formatted())
        return

    if not args.multi_instance:
        client = EmbargoClient(host = args.host, port = args.port)

        if client.check():
            logging.info('instance already running')
            if args.files:
                for file in args.files:
                    client.open_file(os.path.abspath(file))
            return

    app = EmbargoApp(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    compiled = __file__ == os.path.split(__file__)[-1]

    models.create(engine)

    try:
        Context.init(app, compiled = compiled)
    except DBLoadException:
        if not DBUpdateDialog().exec_() == QDialog.Accepted:
            return
        Context.init(app, compiled = compiled)

    init_deck_serializers()

    main_window = MainWindow()

    Context.main_window = main_window

    sys.excepthook = _get_exception_hook(main_window)

    if not args.no_server:
        server = EmbargoServer(host = args.host, port = args.port)
        server.start()

    main_window.showMaximized()

    if Context.settings.value('auto_login', False, bool):
        LOGIN_CONTROLLER.re_login()

    if args.files:
        for path in args.files:
            Context.open_file.emit(path)

    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
