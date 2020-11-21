import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from deckeditor.components.settings.settingeditor import (
    SettingEditor, OptionsSettingEditor, BooleanSettingEditor, StringSettingEditor, AlchemySettingEditor
)
from deckeditor.context.context import Context
from deckeditor.models.cubes.alignment.aligners import ALIGNER_TYPE_MAP
from deckeditor.store.models import SortMacro
from deckeditor.utils.dialogs import SingleInstanceDialog
from deckeditor.components.settings import settings


class SettingsPane(QWidget):

    def __init__(self, setting_editors: t.Sequence[SettingEditor]):
        super().__init__()

        layout = QtWidgets.QFormLayout(self)
        layout.setAlignment(QtCore.Qt.AlignTop)

        for setting in setting_editors:
            setting.render(layout)


class SettingsTreeItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, category_name: str, settings_pane: SettingsPane):
        super().__init__()
        self._settings_pane = settings_pane
        self.setData(0, 0, category_name)

    @property
    def settings_pane(self) -> SettingsPane:
        return self._settings_pane


class SettingsDialog(SingleInstanceDialog):
    set_value = pyqtSignal(str, object, SettingEditor)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Settings')

        self._settings_map = (
            (
                'General',
                (
                    OptionsSettingEditor(
                        settings.DEFAULT_CARD_VIEW_TYPE,
                        'Default layout of focus card view.',
                        ('image', 'text', 'both'),
                    ),
                    BooleanSettingEditor(
                        settings.FRAMELESS,
                        'Removes title bar of main window.',
                    ),
                ),
                (),
            ),
            (
                'Cards View',
                (
                    BooleanSettingEditor(
                        settings.DEFAULT_CUBEVIEW_HEADER_HIDDEN,
                        'Header collapsed by default.',
                    ),
                    BooleanSettingEditor(
                        settings.IMAGE_VIEW_SCROLL_DEFAULT_ZOOM,
                        'If unchecked, scroll wheel scrolls view vertically, hold ctrl while scrolling to zoom.',
                    ),
                    BooleanSettingEditor(
                        settings.SELECT_ON_COVERED_PARTS,
                        'If checked, select all cards intersecting rubber band on completion, also cards '
                        'covered by other cards.',
                    ),
                    BooleanSettingEditor(
                        settings.ON_VIEW_CARD_COUNT,
                        'Show card count / selection info on top of card view.',
                    ),
                    BooleanSettingEditor(
                        settings.FIT_ALL_CARDS,
                        'When fitting view, always fit all cards in view, instead of only the selected if present.',
                    ),
                    BooleanSettingEditor(
                        settings.DOUBLECLICK_MATCH_ON_CARDBOARDS,
                        'When ctrl doubleclicking a card, select all cardboards matching instead of printings.',
                    ),
                    OptionsSettingEditor(
                        settings.DEFAULT_ALIGNER_TYPE,
                        'Aligner type used for new card views.',
                        tuple(ALIGNER_TYPE_MAP.keys()),
                    ),
                ),
                (),
            ),
            (
                'Files',
                (
                    BooleanSettingEditor(
                        settings.AUTO_SORT_NON_EMB_FILES_ON_OPEN,
                        'Auto sort non emb files on open.',
                    ),
                    AlchemySettingEditor(
                        settings.AUTO_SORT_MACRO_ID,
                        'Macro to use for auto sorting files on open.',
                        SortMacro,
                        SortMacro.name,
                    ),
                    BooleanSettingEditor(
                        settings.CONFIRM_CLOSING_MODIFIED_FILE,
                        'Files count as having been modified, even if it is just moving cards around in the same zone.'
                        ' Will be changed eventually.',
                    ),
                ),
                (),
            ),
            (
                'Connection',
                (
                    BooleanSettingEditor(
                        settings.AUTO_LOGIN,
                        'Automatically attempt login on start up.',
                    ),
                ),
                (),
            ),
            (
                'Limited',
                (
                    BooleanSettingEditor(
                        settings.DEFAULT_FOCUS_TRAP_SUB_PRINTING,
                        'Default focus appropriate sub-printing of trap during hover-based focus instead of entire '
                        'trap.',
                    ),
                    BooleanSettingEditor(
                        settings.FLATTEN_RECURSIVELY,
                        'Flatten all flattenable children of af trap instead of of one level at a time.',
                    ),
                    BooleanSettingEditor(
                        settings.ALWAYS_FLATTEN_ALL,
                        'Always flatten all, instead of only selected, when cards are selected.',
                    ),
                    BooleanSettingEditor(
                        settings.DONT_AUTO_FLATTEN_BIG,
                        'Dont flatten big traps when flattening all or recursively.',
                    ),
                ),
                (
                    (
                        'Draft',
                        (
                            BooleanSettingEditor(
                                settings.NOTIFY_ON_BOOSTER_ARRIVED,
                                'Display OS notification when new pack arrives and application does not have focus.',
                            ),
                            BooleanSettingEditor(
                                settings.HIDE_LOBBIES_ON_NEW_DRAFT,
                                'Applies both on new drafts and reconnect.',
                            ),
                            BooleanSettingEditor(
                                settings.INFER_PICK_BURN,
                                'When burn drafting, try to infer whether a pick is a burn or not when appropriate.',
                            ),
                            BooleanSettingEditor(
                                settings.PICK_ON_DOUBLE_CLICK,
                                'Allow picking by double clicking card.',
                            ),
                            BooleanSettingEditor(
                                settings.GHOST_CARDS,
                                'Show cards from booster that did not wheel as greyed out.',
                            ),
                        ),
                        (),
                    ),
                ),
            ),
            (
                'images',
                (
                    BooleanSettingEditor(
                        settings.REMOTE_IMAGES,
                        'Get images from server instead of generating locally.',
                    ),
                    StringSettingEditor(
                        settings.REMOTE_IMAGE_URL,
                        'Where to get remote images from.',
                    ),
                    BooleanSettingEditor(
                        settings.ALLOW_LOCAL_IMAGE_FALLBACK,
                        'Generate images locally if they are unavailable remotely.',
                    ),
                    BooleanSettingEditor(
                        settings.ALLOW_DISK_WITH_LOCAL_IMAGES,
                        'If false, never cache or load images from disk',
                    )
                ),
                (),
            ),
            (
                'db',
                (
                    BooleanSettingEditor(
                        settings.SQL_DB,
                        'Less start-up overhead and memory usage, but slower application in general, especially searching.',
                    ),
                    StringSettingEditor(
                        settings.SQL_HOST,
                        'Sql database host.',
                    ),
                    StringSettingEditor(
                        settings.SQL_DATABASE_NAME,
                        'Sql database name.',
                    ),
                    StringSettingEditor(
                        settings.SQL_USER,
                        'Sql database user.',
                    ),
                    StringSettingEditor(
                        settings.SQL_PASSWORD,
                        'Sql database password.',
                        hide_text = True,
                    ),
                    StringSettingEditor(
                        settings.SQL_DIALECT,
                        'Sql database dialect.',
                    ),
                    StringSettingEditor(
                        settings.SQL_DRIVER,
                        'Sql database driver.',
                    ),
                ),
                (),
            ),
            (
                'store',
                (
                    BooleanSettingEditor(
                        settings.EXTERNAL_STORE_DB,
                        'If false just use sqlite.',
                    ),
                    StringSettingEditor(
                        settings.EXTERNAL_DATABASE_NAME,
                        'Name of database for storage.',
                    ),
                ),
                (),
            ),
        )

        self._setting_changes: t.MutableMapping[SettingEditor, t.Any] = {}

        self._categories_tree = QtWidgets.QTreeWidget()
        self._categories_tree.setColumnCount(1)
        self._categories_tree.setHeaderHidden(True)
        self._categories_tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._build_tree(self._settings_map, self._categories_tree)

        self._settings_pane = QtWidgets.QScrollArea()

        self._categories_tree.currentItemChanged.connect(self._handle_category_selected)

        self._description_box = QtWidgets.QTextEdit()
        self._description_box.setReadOnly(True)

        self._cancel_button = QtWidgets.QPushButton('Cancel')
        self._cancel_button.clicked.connect(self.cancel)

        self._apply_button = QtWidgets.QPushButton('Apply')
        self._apply_button.clicked.connect(self.apply)

        self._ok_button = QtWidgets.QPushButton('OK')
        self._ok_button.clicked.connect(self.ok)

        self._apply_button.setEnabled(False)

        layout = QtWidgets.QVBoxLayout(self)

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(self._categories_tree, 1)
        top_layout.addWidget(self._settings_pane, 3)

        layout.addLayout(top_layout, 3)
        layout.addWidget(self._description_box, 1)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self._cancel_button)
        buttons_layout.addWidget(self._apply_button)
        buttons_layout.addWidget(self._ok_button)

        layout.addLayout(buttons_layout)

    def _finish(self) -> None:
        self._setting_changes.clear()
        self._apply_button.setEnabled(False)

    def ok(self) -> None:
        self.apply()
        self._finish()
        self.accept()

    def cancel(self) -> None:
        self._finish()
        self.reject()

    def apply(self) -> None:
        if any(editor.setting.requires_restart for editor in self._setting_changes):
            Context.notification_message.emit('Some of the settings changes requires restarting to take effect.')

        for setting, value in self._setting_changes.items():
            setting.setting.set_value(value)

    def _walk_settings_tree(
        self,
        tree: t.Sequence[t.Tuple[str, t.Sequence[SettingEditor], t.Sequence]],
    ) -> t.Iterator[SettingEditor]:
        for name, settings, children in tree:
            for setting in settings:
                yield setting
            yield from self._walk_settings_tree(children)

    def _build_tree(
        self,
        tree: t.Sequence[t.Tuple[str, t.Sequence[SettingEditor], t.Sequence]],
        item: t.Union[QtWidgets.QTreeWidget, QtWidgets.QTreeWidget],
    ) -> None:
        for name, settings, children in tree:
            _item = SettingsTreeItem(
                name,
                SettingsPane(
                    settings,
                ),
            )

            for setting in settings:
                setting.selected.connect(self._handle_setting_chosen)
                setting.show_description.connect(lambda s, d: self._description_box.setText(d))

            if isinstance(item, QtWidgets.QTreeWidget):
                item.addTopLevelItem(_item)
            else:
                item.addChild(_item)

            self._build_tree(children, _item)

    def _handle_category_selected(self, current: SettingsTreeItem, previous: SettingsTreeItem) -> None:
        self._settings_pane.takeWidget()
        self._settings_pane.setWidget(current.settings_pane)

    def _handle_setting_chosen(self, editor: SettingEditor, value: t.Any) -> None:
        if value == editor.setting.get_value():
            try:
                del self._setting_changes[editor]
            except KeyError:
                pass
        else:
            self._setting_changes[editor] = value

        self._apply_button.setEnabled(bool(self._setting_changes))

    def exec_(self) -> int:
        for setting in self._walk_settings_tree(self._settings_map):
            setting.reset()
        return super().exec_()
