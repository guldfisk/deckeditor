from __future__ import annotations

import argparse
import io
import logging
import os
import pickle
import sys
import time
import traceback
import typing as t

import requests
from magiccube.collections.delta import CubeDeltaOperation
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QMainWindow,
    QMessageBox,
    QUndoView,
    QWidget,
)
from yeetlong.multiset import Multiset

from deckeditor import paths, values
from deckeditor.application.embargo import EmbargoApp
from deckeditor.authentication.login import LOGIN_CONTROLLER
from deckeditor.components.authentication.login import LoginDialog
from deckeditor.components.cardadd.cardadder import PrintingSelector
from deckeditor.components.cardview.cubeableview import CubeableView
from deckeditor.components.db.info import DBInfoDialog
from deckeditor.components.db.update import DBUpdateDialog
from deckeditor.components.editables.editablestabs import (
    EditablesTabs,
    FileOpenException,
    FileSaveException,
)
from deckeditor.components.help.about import AboutDialog
from deckeditor.components.lobbies.view import LobbiesView, LobbyModelClientConnection
from deckeditor.components.sample.hand import SampleHandDialog
from deckeditor.components.sealed.view import LimitedSessionsView
from deckeditor.components.settings import settings
from deckeditor.components.settings.dialog import SettingsDialog
from deckeditor.components.views.cubeedit.graphical.cubeimagepreview import (
    GraphicsMiniView,
)
from deckeditor.components.views.cubeedit.graphical.sortdialog import EditMacroesDialog
from deckeditor.components.views.editables.editable import TabType
from deckeditor.components.views.editables.multicubesview import MultiCubesView
from deckeditor.context.context import Context, DbType
from deckeditor.models.cubes.alignment.init import init_aligners
from deckeditor.models.cubes.scenetypes import SceneType
from deckeditor.models.deck import Deck, DeckModel, Pool, TabModel
from deckeditor.notifications.frame import NotificationFrame
from deckeditor.serialization.tabmodelserializer import init_deck_serializers
from deckeditor.server.client import EmbargoClient
from deckeditor.server.server import EmbargoServer
from deckeditor.sorting.custom import CustomSortMap
from deckeditor.store import EDB, models
from deckeditor.utils.actions import WithActions
from deckeditor.utils.version import version_formatted
from deckeditor.values import SUPPORTED_EXTENSIONS
from deckeditor.views.tournaments.matches import ScheduledMatchesView


class MainView(QWidget):
    def __init__(self, parent: t.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(3, 0, 3, 0)

        self.editables_tabs = EditablesTabs()

        Context.editor = self.editables_tabs

        layout.addWidget(self.editables_tabs)

        self.setLayout(layout)


class Dock(QtWidgets.QDockWidget, WithActions):
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
        self.setContentsMargins(3, 0, 3, 0)

        self._wants_focus = wants_focus

        self._create_action("Hide", self.hide, "ESC")

    @property
    def wants_focus(self) -> bool:
        return self._wants_focus


class MainWindow(QMainWindow, WithActions):
    pool_generated = QtCore.pyqtSignal(Multiset)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowIcon(QtGui.QIcon(paths.ICON_PATH))
        if settings.FRAMELESS.get_value():
            self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self._notification_frame = NotificationFrame(self)

        self.setWindowTitle(values.APPLICATION_NAME)

        self.layout().setContentsMargins(0, 0, 0, 0)

        self._printing_view = CubeableView(self)
        Context.focus_card_changed.connect(self._printing_view.new_cubeable)

        self._login_status_label = QtWidgets.QLabel("")
        LOGIN_CONTROLLER.login_success.connect(lambda u, h: self._login_status_label.setText(f"{u.username}@{h}"))
        LOGIN_CONTROLLER.login_failed.connect(lambda e: self._login_status_label.setText(""))
        LOGIN_CONTROLLER.login_terminated.connect(lambda: self._login_status_label.setText(""))
        LOGIN_CONTROLLER.login_pending.connect(lambda u, h: self._login_status_label.setText(f"logging in @ {h}"))

        self.statusBar().setContentsMargins(10, 0, 10, 0)
        self.statusBar().addPermanentWidget(self._login_status_label)
        Context.status_message.connect(lambda m, _t: self.statusBar().showMessage(m, _t))

        self.statusBar().addPermanentWidget(QtWidgets.QLabel(version_formatted()))

        self._card_view_dock = Dock("Card View", "card_view_dock", self, self._printing_view, wants_focus=False)
        Context.focus_freeze_changed.connect(
            lambda frozen: self._card_view_dock.setWindowTitle("Card View" + (" (frozen)" if frozen else ""))
        )

        self._card_adder = PrintingSelector(self)
        self._card_adder.add_printings.connect(self._on_add_printings)

        self._card_adder_dock = Dock("Card Adder", "card adder dock", self, self._card_adder)

        self._undo_view = QUndoView(Context.undo_group)

        self._undo_view_dock = Dock("Undo View", "undo view dock", self, self._undo_view)

        self._lobby_view = LobbiesView(LobbyModelClientConnection())
        self._lobby_view_dock = Dock(
            "Lobby View",
            "lobbies",
            self,
            self._lobby_view,
            allowed_areas=QtCore.Qt.RightDockWidgetArea
            | QtCore.Qt.LeftDockWidgetArea
            | QtCore.Qt.BottomDockWidgetArea,
        )

        self._cube_view_minimap = GraphicsMiniView()
        Context.focus_scene_changed.connect(lambda scene: self._cube_view_minimap.set_scene(scene))

        self._cube_view_minimap_dock = Dock("Minimap", "minimap", self, self._cube_view_minimap, wants_focus=False)

        self._limited_sessions_view = LimitedSessionsView()

        self._limited_sessions_dock = Dock("Limited", "Limited", self, self._limited_sessions_view)

        self._matches_view = ScheduledMatchesView()

        self._matches_view_dock = Dock("Matches", "Matches", self, self._matches_view)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._card_adder_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._card_view_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._undo_view_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._lobby_view_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._cube_view_minimap_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._limited_sessions_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._matches_view_dock)

        self._card_view_dock.hide()
        self._card_adder_dock.hide()
        self._undo_view_dock.hide()
        self._lobby_view_dock.hide()
        self._cube_view_minimap_dock.hide()
        self._limited_sessions_dock.hide()
        self._matches_view_dock.hide()

        self._main_view = MainView(self)

        self.setCentralWidget(self._main_view)

        menu_bar = self.menuBar()

        all_menus = [
            (
                menu_bar.addMenu("File"),
                (
                    ("New Deck", "Ctrl+N", self._new_deck),
                    ("Open Deck", "Ctrl+O", lambda: self.open(Deck)),
                    ("Open Pool", "Ctrl+P", lambda: self.open(Pool)),
                    ("Save", "Ctrl+S", self._save),
                    ("Save As", "Ctrl+Shift+S", self._save_as),
                    ("Export Deck", "Ctrl+Shift+E", self._export_deck),
                    ("Close Tab", "Ctrl+W", self._close_tab),
                    "line",
                    ("Exit", "Ctrl+Q", self.close),
                ),
            ),
            (
                menu_bar.addMenu("Edit"),
                (
                    ("Undo", "Ctrl+Z", Context.undo_group.undo),
                    ("Redo", "Ctrl+Shift+Z", Context.undo_group.redo),
                    "line",
                    ("Add cards", "Ctrl+F", self._add_cards),
                    ("Sort Macroes", "Ctrl+M", self._edit_sort_macroes),
                ),
            ),
            (
                menu_bar.addMenu("View"),
                (
                    ("Card View", "Meta+1", lambda: self._toggle_dock_view(self._card_view_dock)),
                    ("Card Adder", "Meta+2", lambda: self._toggle_dock_view(self._card_adder_dock)),
                    ("Limited", "Meta+3", lambda: self._toggle_dock_view(self._limited_sessions_dock)),
                    ("Lobbies", "Meta+4", lambda: self._toggle_dock_view(self._lobby_view_dock)),
                    ("Matches", "Meta+5", lambda: self._toggle_dock_view(self._matches_view_dock)),
                    ("Undo", None, lambda: self._toggle_dock_view(self._undo_view_dock)),
                    ("Minimap", None, lambda: self._toggle_dock_view(self._cube_view_minimap_dock)),
                ),
            ),
            (
                menu_bar.addMenu("Connect"),
                (
                    ("Login", "Ctrl+L", LoginDialog(self).exec_),
                    ("Logout", None, LOGIN_CONTROLLER.log_out),
                ),
            ),
            (
                menu_bar.addMenu("Draft"),
                (
                    ("Go To Latest", "Alt+Up", self._draft_history_wrapper("go_to_latest")),
                    ("Go Back", "Alt+Left", self._draft_history_wrapper("go_backwards")),
                    ("Go Forward", "Alt+Right", self._draft_history_wrapper("go_forward")),
                    ("Go To Start", "Alt+Down", self._draft_history_wrapper("go_to_start")),
                ),
            ),
            (menu_bar.addMenu("Simulate"), (("Sample Hand", "Ctrl+H", self._sample_hand),)),
            (
                menu_bar.addMenu("Preferences"),
                (("Settings", "Ctrl+Alt+S", lambda: SettingsDialog.get().exec_()),),
            ),
            (
                menu_bar.addMenu("DB"),
                (
                    ("Info", None, lambda: DBInfoDialog().exec_()),
                    ("Update", None, lambda: DBUpdateDialog().exec_()),
                    ("Validate", None, lambda: LOGIN_CONTROLLER.validate(True)),
                ),
            ),
            (
                menu_bar.addMenu("Help"),
                (("About", None, lambda: AboutDialog().exec_()),),
            ),
        ]

        if Context.debug:
            all_menus.append(
                (
                    menu_bar.addMenu("Test"),
                    (("Test", "Ctrl+T", self._test),),
                )
            )

        for menu, lines in all_menus:
            for line in lines:
                if line == "line":
                    menu.addSeparator()
                else:
                    name, shortcut, action = line
                    _action = QAction(name, self)
                    if shortcut:
                        _action.setShortcut(shortcut)
                    _action.triggered.connect(action)
                    menu.addAction(_action)

        self._create_action("toggle freeze focus", Context.toggle_frozen_focus, "Alt+F")

        self._reset_dock_width = 500
        self._reset_dock_height = 1200

        self.resizeDocks([self._card_view_dock], [self._reset_dock_width], QtCore.Qt.Horizontal)

        Context.notification_message.connect(self._notification_frame.notify)
        Context.draft_started.connect(self._on_draft_started)

        self._load_state()

    def _test(self) -> None:
        raise Exception("real cool test")
        # from notifypy import Notify
        # notification = Notify()
        # notification.title = 'New pack'
        # notification.message = f'SOME SHIT'
        # notification.application_name = 'Embargo Edit'
        # notification.icon = paths.ICON_PATH
        # notification.send()

    def _sample_hand(self) -> None:
        tab = self._main_view.editables_tabs.currentWidget()
        if isinstance(tab.editable, MultiCubesView) and SceneType.MAINDECK in tab.editable.cube_views_map:
            SampleHandDialog(tab.editable.cube_views_map[SceneType.MAINDECK].cube_scene).exec_()

    def _draft_history_wrapper(self, method: str) -> t.Callable[[], None]:
        def wrapper():
            tab = self._main_view.editables_tabs.currentWidget()
            if tab.tab_type == TabType.DRAFT:
                getattr(tab.editable.draft_model, method)()

        return wrapper

    def _on_draft_started(self, key: str) -> None:
        if settings.HIDE_LOBBIES_ON_NEW_DRAFT.get_value():
            self._lobby_view_dock.hide()

    @property
    def login_status_label(self) -> QtWidgets.QLabel:
        return self._login_status_label

    def _on_add_printings(self, delta_operation: CubeDeltaOperation):
        tab = self._main_view.editables_tabs.currentWidget()
        if tab.tab_type == TabType.DECK:
            tab.undo_stack.push(tab.editable.deck_model.maindeck.get_cube_modification(delta_operation))
        elif tab.tab_type == TabType.POOL:
            tab.undo_stack.push(tab.editable.pool_model.maindeck.get_cube_modification(delta_operation))
        elif tab.tab_type == TabType.DRAFT:
            tab.undo_stack.push(tab.editable.pool_model.maindeck.get_cube_modification(delta_operation))

    def _toggle_dock_view(self, dock: Dock) -> None:
        if dock.wants_focus:
            if dock.hasFocus():
                dock.hide()
            else:
                dock.show()
                dock.activateWindow()
                dock.setFocus()
        else:
            dock.setVisible(not dock.isVisible())

    def _new_deck(self) -> None:
        self._main_view.editables_tabs.setCurrentWidget(self._main_view.editables_tabs.new_deck(DeckModel()))

    def _close_tab(self) -> None:
        self._main_view.editables_tabs.tabCloseRequested.emit(self._main_view.editables_tabs.currentIndex())

    def _edit_sort_macroes(self) -> None:
        EditMacroesDialog().exec_()

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
        if hasattr(self, "_notification_frame"):
            self._notification_frame.stack_notifications()

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
            Context.notification_message.emit("Corrupt file or wrong inferred type.\n{}".format(e))

    def _save(self):
        try:
            self._main_view.editables_tabs.save_tab()
        except FileSaveException:
            Context.notification_message.emit("Invalid extension")

    def _save_as(self):
        try:
            self._main_view.editables_tabs.save_tab_as()
        except FileSaveException:
            Context.notification_message.emit("Invalid file extension")

    def _export_deck(self):
        try:
            self._main_view.editables_tabs.export_deck()
        except FileSaveException:
            Context.notification_message.emit("Invalid extension")

    def save_state(self):
        Context.settings.setValue("geometry", self.saveGeometry())
        Context.settings.setValue("window_state", self.saveState(0))
        self._main_view.editables_tabs.save_session()
        Context.sort_map.save()

    def _load_state(self):
        geometry = Context.settings.value("geometry", None)
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = Context.settings.value("window_state")
        if state is not None:
            self.restoreState(state, 0)
        self._main_view.editables_tabs.load_session()
        try:
            Context.sort_map = CustomSortMap.load()
        except (pickle.UnpicklingError, EOFError):
            Context.notification_message.emit("Failed loading custom sort map")
            return CustomSortMap.empty()

    def closeEvent(self, close_event):
        self.save_state()
        if Context.embargo_server is not None:
            Context.embargo_server.stop()
        Context.pixmap_loader.stop()
        super().closeEvent(close_event)


def _get_exception_hook(main_window: t.Optional[MainWindow] = None) -> t.Callable[[t.Any, t.Any, t.Any], None]:
    def exception_hook(exception_type, exception_value, _traceback):
        separator = "-" * 80
        time_string = time.strftime("%Y-%m-%d, %H:%M:%S")

        traceback_info_file = io.StringIO()
        traceback.print_tb(_traceback, None, traceback_info_file)
        traceback_info_file.seek(0)
        traceback_info = traceback_info_file.read()

        errmsg = "{} {}".format(
            str(exception_type),
            str(exception_value),
        )

        msg = "\n".join((separator, time_string, traceback_info, errmsg, "\n"))

        try:
            if not os.path.exists(paths.APP_DATA_PATH):
                os.makedirs(paths.APP_DATA_PATH)

            with open(paths.LOGS_PATH, "a") as log_file:
                log_file.write(msg)
        except IOError:
            pass

        sys.stderr.write(traceback_info + "\n")
        sys.stderr.write(errmsg + "\n")

        # Promises are buggy
        if issubclass(exception_type, AssertionError):
            return

        if settings.REPORT_ERRORS.get_value() and not Context.debug and Context.cube_api_client:
            Context.cube_api_client.report_error(errmsg, traceback_info)

        errorbox = QMessageBox()
        errorbox.setWindowTitle("OH NO :O")
        errorbox.setText(
            "{}\n{}".format(
                traceback_info,
                errmsg,
            )
        )
        errorbox.exec_()
        if main_window is not None:
            main_window.close()

    return exception_hook


class FilterAll(logging.Filter):
    def filter(self, record):
        return False


def run():
    sys.excepthook = _get_exception_hook()

    arg_parser = argparse.ArgumentParser(description="Edit decks")
    arg_parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="show version",
    )
    arg_parser.add_argument(
        "-m",
        "--multi-instance",
        action="store_true",
        help="allow running in parallel with other instances of Embargo Edit",
    )
    arg_parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="debug mode",
    )
    arg_parser.add_argument(
        "-l",
        "--log-level",
        action="store",
        help="logging level",
        default="debug",
        choices=values.LOGGING_LEVEL_MAP.keys(),
    )
    arg_parser.add_argument(
        "--echo-sql",
        action="store_true",
        help="Echo sql queries",
    )
    arg_parser.add_argument(
        "-n",
        "--no-server",
        action="store_true",
        help="dont start server",
    )
    arg_parser.add_argument(
        "--no-ssl-verify",
        action="store_true",
        help="disable ssl certificate verification for remote connections.",
    )
    arg_parser.add_argument(
        "--db-type",
        type=str,
        nargs="?",
        choices=["sql", "pickle", "default"],
        default="default",
        help='what type of server to use. "default" means use the one defined in application settings',
    )
    arg_parser.add_argument(
        "--port",
        metavar="P",
        type=int,
        nargs="?",
        default=7777,
        help="server port",
    )
    arg_parser.add_argument(
        "--host",
        metavar="H",
        type=str,
        nargs="?",
        default="localhost",
        help="server host",
    )
    arg_parser.add_argument("files", metavar="F", type=str, nargs="*", help="paths of files to open")

    args = arg_parser.parse_args()

    for k, v in logging.Logger.manager.loggerDict.items():
        if isinstance(v, logging.Logger):
            v.handlers[:] = []

    logging.basicConfig(
        format="%(levelname)s %(message)s",
        level=values.LOGGING_LEVEL_MAP[args.log_level],
        stream=sys.stdout,
    )

    logging.getLogger("PIL.PngImagePlugin").addFilter(FilterAll())

    if args.version:
        print(version_formatted())
        return

    if not args.multi_instance:
        client = EmbargoClient(host=args.host, port=args.port)

        if client.check():
            logging.info("instance already running")
            if args.files:
                for file in args.files:
                    client.open_file(os.path.abspath(file))
            return

    init_aligners()
    app = EmbargoApp.init(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    compiled = __file__ == os.path.split(__file__)[-1]

    db_type = DbType(args.db_type)

    if args.no_ssl_verify:
        logging.warning("Running without ssl verification!")
        requests.packages.urllib3.disable_warnings()

    init_args = {
        "compiled": compiled,
        "debug": args.debug,
        "db_type": db_type,
        "echo_sql": args.echo_sql,
        "no_ssl_verify": args.no_ssl_verify,
    }

    try:
        Context.init(app, **init_args)
    except Exception:
        if not DBUpdateDialog().exec_() == QDialog.Accepted:
            return
        Context.init(app, **init_args)

    EDB.init(echo=args.echo_sql)

    models.create(EDB.engine)

    init_deck_serializers()

    main_window = MainWindow()

    Context.main_window = main_window

    sys.excepthook = _get_exception_hook(main_window)

    if not args.no_server:
        Context.embargo_server = EmbargoServer(host=args.host, port=args.port)
        Context.embargo_server.start()

    main_window.showMaximized()

    if not args.multi_instance:
        save_state_timer = QtCore.QTimer()
        save_state_timer.timeout.connect(main_window.save_state)
        save_state_timer.start(1000 * 60 * 3)

    if settings.AUTO_LOGIN.get_value():
        LOGIN_CONTROLLER.re_login()

    if args.files:
        for path in args.files:
            Context.open_file.emit(path)

    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
