from __future__ import annotations

import io
import os
import sys
import time
import traceback
import typing
import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QMainWindow, QAction, QUndoView, QMessageBox, QDialog

from deckeditor.components.sealed.view import LimitedSessionsView
from deckeditor.components.views.editables.pool import PoolView
from yeetlong.multiset import Multiset

from mtgorp.db import create
from mtgorp.db.load import DBLoadException
from mtgorp.managejson import download
from mtgorp.managejson.update import check, update_last_updated

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


class MainView(QWidget):

    def __init__(self, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout()

        self.editables_tabs = EditablesTabs()

        Context.editor = self.editables_tabs

        layout.addWidget(self.editables_tabs)

        self.setLayout(layout)


class MainWindow(QMainWindow, CardAddable):
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

        self._card_adder = CardAdder(self)
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

        self._limited_sessions_view = LimitedSessionsView()

        self._limited_sessions_dock = QtWidgets.QDockWidget('Sealed', self)
        self._limited_sessions_dock.setObjectName('sealed')
        self._limited_sessions_dock.setWidget(self._limited_sessions_view)
        self._limited_sessions_dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

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
                ('Open Deck', 'Ctrl+O', lambda: self._open(Deck)),
                ('Open Pool', 'Ctrl+P', lambda: self._open(Pool)),
                ('Save', 'Ctrl+S', self._save),
                ('Save As', 'Ctrl+Shift+S', self._save_as),
                ('Export Deck', 'Ctrl+Shift+E', self._export_deck),
                # ('Save pool', 'Ctrl+l', self.save_pool),
                ('Close Tab', 'Ctrl+W', self._close_tab),

            ),
            menu_bar.addMenu('Edit'): (
                ('Undo', 'Ctrl+Z', Context.undo_group.undo),
                ('Redo', 'Ctrl+Shift+Z', Context.undo_group.redo),
            ),
            # menu_bar.addMenu('Deck'): (
            #     # ('Maindeck', 'Ctrl+1', lambda: self._focus_deck_zone(DeckZoneType.MAINDECK)),
            #     # ('Sideboard', 'Ctrl+2', lambda: self._focus_deck_zone(DeckZoneType.SIDEBOARD)),
            #     # ('Pool', 'Ctrl+3', lambda: self._focus_deck_zone(DeckZoneType.POOL)),
            #     # ('Exclusive Maindeck', 'Alt+Ctrl+1', self._exclusive_maindeck),
            #     # ('Exclusive Sideboard', 'Alt+Ctrl+2', self._exclusive_sideboard),
            #     # ('Exclusive Pool', 'Alt+Ctrl+3', self._exclusive_pool),
            # ),
            # menu_bar.addMenu('Generate'): (
            #     # ('Sealed pool', 'Ctrl+G', self._generate_pool),
            #     # ('Cube Pools', 'Ctrl+C', self.generate_cube_pools),
            # ),
            menu_bar.addMenu('Add'): (
                # ('Test Add', 'Ctrl+W', self._test_add),
                ('Add cards', 'Ctrl+F', self._add_cards),
            ),
            # menu_bar.addMenu('Select'): (
            #     # ('All', 'Ctrl+A', self._select_all),
            #     # ('Clear Selection', 'Ctrl+D', self._clear_selection),
            #     # ('Select Matching', 'Ctrl+E', self._search_select),
            # ),
            menu_bar.addMenu('View'): (
                ('Card View', 'Meta+1', lambda: self._toggle_dock_view(self._card_view_dock)),
                ('Card Adder', 'Meta+2', lambda: self._toggle_dock_view(self._card_adder_dock)),
                # ('Deck List View', 'Meta+3', lambda: self._toggle_dock_view(self._deck_list_docker)),
                ('Lobbies', 'Meta+4', lambda: self._toggle_dock_view(self._lobby_view_dock)),
                ('Undo', 'Meta+5', lambda: self._toggle_dock_view(self._undo_view_dock)),
                ('Minimap', 'Meta+6', lambda: self._toggle_dock_view(self._cube_view_minimap_dock)),
                ('Sealed', 'Meta+7', lambda: self._toggle_dock_view(self._limited_sessions_dock)),
            ),
            # menu_bar.addMenu('Test'): (
            #     ('Test', 'Ctrl+T', self._test),
            # ),
            menu_bar.addMenu('Connect'): (
                ('Login', 'Ctrl+L', LoginDialog(self).exec_),
                ('Logout', None, lambda: None),
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

        self._reset_dock_width = 500
        self._reset_dock_height = 1200

        Context.notification_message.connect(self._notification_frame.notify)

        self._load_state()

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

    @staticmethod
    def _toggle_dock_view(dock: QtWidgets.QDockWidget):
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

    def _test(self):
        raise Exception('test')

    def resizeEvent(self, resize_event: QtGui.QResizeEvent):
        if hasattr(self, '_notification_frame'):
            self._notification_frame.stack_notifications()

    def generate_cube_pools(self):
        pass

    def _open(self, target: t.Type[TabModel] = Deck):
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
        except FileOpenException:
            Context.notification_message.emit('Corrupt file or wrong inferred type')

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

    def _save_state(self):
        Context.settings.setValue('geometry', self.saveGeometry())
        Context.settings.setValue('window_state', self.saveState(0))
        self._main_view.editables_tabs.save_session()

    def _load_state(self):
        geometry = Context.settings.value('geometry', None)
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = Context.settings.value('window_state')
        if state is not None:
            self.restoreState(state, 0)
        self._main_view.editables_tabs.load_session()

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
        Context.init(app)
    except DBLoadException:
        if not MtgOrpDialog().exec_() == QDialog.Accepted:
            return
        Context.init(app)

    main_window = MainWindow()

    sys.excepthook = _get_exception_hook(main_window)

    # app.aboutToQuit.connect(Context.settings.)

    main_window.showMaximized()

    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
