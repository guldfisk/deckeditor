import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QWidget

from deckeditor.components.settings.setting import BooleanSetting, Setting, OptionsSetting
from deckeditor.context.context import Context


class SettingsPane(QWidget):

    def __init__(self, settings: t.Sequence[Setting]):
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignTop)

        for setting in settings:
            setting.render(layout)


class SettingsTreeItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, category_name: str, settings_pane: SettingsPane):
        super().__init__()
        self._settings_pane = settings_pane
        self.setData(0, 0, category_name)

    @property
    def settings_pane(self) -> SettingsPane:
        return self._settings_pane


class SettingsDialog(QDialog):
    set_value = pyqtSignal(str, object, Setting)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Settings')

        self._settings_map = (
            (
                'General',
                (
                    BooleanSetting(
                        'default_cubeview_header_hidden',
                        'Cubeview header collapsed by default',
                        'Cubeview header collapsed by default',
                        True,
                    ),
                    BooleanSetting(
                        'image_view_scroll_default_zoom',
                        'Zoom in cubeview with scroll wheel',
                        'If unchecked, scroll wheel scrolls view vertically, hold ctrl while scrolling to zoom',
                        True,
                    ),
                    OptionsSetting(
                        'default_card_view_type',
                        'Default card view',
                        'Default layout of focus card view',
                        'image',
                        ('image', 'text', 'both'),
                    ),
                ),
                (),
            ),
            (
                'Connection',
                (
                    BooleanSetting(
                        'auto_login',
                        'Auto login',
                        'Automatically attempt login on start up',
                        False,
                    ),
                ),
                (),
            ),
            (
                'Limited',
                (
                    BooleanSetting(
                        'default_focus_trap_sub_printing',
                        'Default focus trap sub-printings',
                        'Default focus appropriate sub-printing of trap during hover-based focus instead of entire '
                        'trap.',
                        False,
                    ),
                ),
                (
                    (
                        'Draft',
                        (
                            BooleanSetting(
                                'notify_on_booster_arrived',
                                'Booster notification',
                                'Display OS notification when new pack arrives and application does not have focus.',
                                True,
                            ),
                        ),
                        (),
                    ),
                ),
            ),
        )

        self._setting_changes: t.MutableMapping[Setting, t.Any] = {}

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
        self._cancel_button.clicked.connect(self.reject)

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

    def ok(self) -> None:
        self.apply()
        self.accept()

    def apply(self) -> None:
        if any(setting.requires_restart for setting in self._setting_changes):
            Context.notification_message.emit('Some of the settings changes requires restarting to take effect.')

        for setting, value in self._setting_changes.items():
            Context.settings.setValue(setting.key, value)

        self._setting_changes.clear()
        self._apply_button.setEnabled(False)

    def _build_tree(
        self,
        tree: t.Sequence[t.Tuple[str, t.Sequence[Setting], t.Sequence]],
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

    def _handle_setting_chosen(self, setting: Setting, value: t.Any) -> None:
        if value == Context.settings.value(setting.key, setting.default_value, setting.setting_type):
            try:
                del self._setting_changes[setting]
            except KeyError:
                pass
        else:
            self._setting_changes[setting] = value

        self._apply_button.setEnabled(bool(self._setting_changes))
