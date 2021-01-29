import json
import typing as t

from PyQt5.QtCore import QSettings

from deckeditor.context.context import Context


T = t.TypeVar('T')


class Setting(t.Generic[T]):
    _type: t.Type

    def __init__(self, key: str, name: str, default: T, *, requires_restart: bool = False):
        self._key = key
        self._name = name
        self._default = default
        self._requires_restart = requires_restart

    @property
    def key(self):
        return self._key

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        return self._default

    @property
    def requires_restart(self) -> bool:
        return self._requires_restart

    def _serialize(self, v: T) -> t.Any:
        return v

    def _deserialize(self, v: t.Any) -> T:
        return v

    def get_value(self, settings: t.Optional[QSettings] = None) -> T:
        return self._deserialize(
            (Context.settings if settings is None else settings).value(self._key, self._default, self._type)
        )

    def set_value(self, value: T, settings: t.Optional[QSettings] = None):
        (Context.settings if settings is None else settings).setValue(self._key, self._serialize(value))


class BooleanSetting(Setting[bool]):
    _type = bool


class IntegerSetting(Setting[int]):
    _type = int


class StringSetting(Setting[str]):
    _type = str


class JsonSetting(Setting[t.Mapping[str, t.Any]]):
    _type = str

    def _serialize(self, v: T) -> t.Any:
        return json.dumps(v)

    def _deserialize(self, v: t.Any) -> T:
        return json.loads(v)


DEFAULT_CARD_VIEW_TYPE = StringSetting('default_card_view_type', 'Default card view', 'image')
FRAMELESS = BooleanSetting('frameless', 'Frameless', True, requires_restart = True)
LAZY_TABS = BooleanSetting('lazy_tabs', 'Lazy Tabs', True, requires_restart = True)

DEFAULT_CUBEVIEW_HEADER_HIDDEN = BooleanSetting('default_cubeview_header_hidden', 'Header collapsed by default', True)
IMAGE_VIEW_SCROLL_DEFAULT_ZOOM = BooleanSetting('image_view_scroll_default_zoom', 'Zoom with scroll wheel', True)
SELECT_ON_COVERED_PARTS = BooleanSetting('select_on_covered_parts', 'Select all cards intersecting rubber band', False)
ON_VIEW_CARD_COUNT = BooleanSetting('on_view_card_count', 'Show card count overlay', True)
FIT_ALL_CARDS = BooleanSetting('fit_all_cards', 'Fit all cards', False)
DOUBLECLICK_MATCH_ON_CARDBOARDS = BooleanSetting('doubleclick_match_on_cardboards', 'Doubleclick matches on cardboards', True)
SCENE_DEFAULTS = JsonSetting('scene_default', 'Scene Defaults', "{}")
AUTO_SORT_NON_EMB_FILES_ON_OPEN = BooleanSetting('auto_sort_non_emb_files_on_open', 'Auto sort files on open', True)

CONFIRM_CLOSING_MODIFIED_FILE = BooleanSetting('confirm_closing_modified_file', 'Confirm closing modified / unsaved files', True)
AUTO_LOGIN = BooleanSetting('auto_login', 'Auto login', False)
DEFAULT_FOCUS_TRAP_SUB_PRINTING = BooleanSetting('default_focus_trap_sub_printing', 'Default focus trap sub-printing', False)
FLATTEN_RECURSIVELY = BooleanSetting('flatten_recursively', 'Flatten recursively', True)
ALWAYS_FLATTEN_ALL = BooleanSetting('always_flatten_all', 'Always flatten all', False)
DONT_AUTO_FLATTEN_BIG = BooleanSetting('dont_auto_flatten_big', 'Do not auto flatten big traps', False)
NOTIFY_ON_BOOSTER_ARRIVED = BooleanSetting('notify_on_booster_arrived', 'Booster notification', True)
HIDE_LOBBIES_ON_NEW_DRAFT = BooleanSetting('hide_lobbies_on_new_draft', 'Hide lobby view when draft starts', True)
INFER_PICK_BURN = BooleanSetting('infer_pick_burn', 'Infer pick burn', True)
PICK_ON_DOUBLE_CLICK = BooleanSetting('pick_on_double_click', 'Double click pick', True)
GHOST_CARDS = BooleanSetting('ghost_cards', 'Ghost cards', True)

IMAGE_CACHE_SIZE = IntegerSetting('image_cache_size', 'Image cache size', 64, requires_restart = True)
REMOTE_IMAGES = BooleanSetting('remote_images', 'Remote images', False, requires_restart = True)
REMOTE_IMAGE_URL = StringSetting('remote_image_url', 'Remote images url', 'http://prohunterdogkeeper.dk', requires_restart = True)
ALLOW_LOCAL_IMAGE_FALLBACK = BooleanSetting('allow_local_image_fallback', 'Allow local fallback', True, requires_restart = True)
ALLOW_DISK_WITH_LOCAL_IMAGES = BooleanSetting(
    'allow_disk_with_local_images',
    'Save and load images on disk when using remote images',
    False,
    requires_restart = True,
)

SQL_DB = BooleanSetting('sql_db', 'Use sql database for card info', False, requires_restart = True)
SQL_HOST = StringSetting('sql_host', 'Sql database host', 'localhost', requires_restart = True)
SQL_DATABASE_NAME = StringSetting('sql_database_name', 'Sql database name', 'mtg', requires_restart = True)
SQL_USER = StringSetting('sql_user', 'Sql database user', 'user', requires_restart = True)
SQL_PASSWORD = StringSetting('sql_password', 'Sql database password', '', requires_restart = True)
SQL_DIALECT = StringSetting('sql_dialect', 'Sql database dialect', 'mysql', requires_restart = True)
SQL_DRIVER = StringSetting('sql_driver', 'Sql driver', 'mysqldb', requires_restart = True)

EXTERNAL_STORE_DB = BooleanSetting('external_store_db', 'Use external database for application storage', False, requires_restart = True)
EXTERNAL_DATABASE_NAME = StringSetting('external_database_name', 'External database name', 'embargo', requires_restart = True)
