import os

from appdirs import AppDirs


APP_DATA_PATH = AppDirs("embargoedit", "embargoedit").user_data_dir

LOGS_PATH = os.path.join(APP_DATA_PATH, "errors.log")
SESSION_PATH = os.path.join(APP_DATA_PATH, "session.dmp")
DEBUG_SESSION_PATH = os.path.join(APP_DATA_PATH, "session_debug.dmp")
CUSTOM_SORT_MAP_PATH = os.path.join(APP_DATA_PATH, "sort_map.dmp")
DB_PATH = os.path.join(APP_DATA_PATH, "store.db")


RESOURCE_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "resources",
)

ICON_PATH = os.path.join(
    RESOURCE_PATH,
    "icon.png",
)

ICONS_PATH = os.path.join(
    RESOURCE_PATH,
    "icons",
)
