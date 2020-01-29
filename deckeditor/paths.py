import os

from appdirs import AppDirs


APP_DATA_PATH = AppDirs('embargoedit', 'embargoedit').user_data_dir

LOGS_PATH = os.path.join(APP_DATA_PATH, 'errors.log')
SESSION_PATH = os.path.join(APP_DATA_PATH, 'session.dmp')


RESOURCE_PATH = os.path.join(
    os.path.dirname(
        os.path.realpath(__file__)
    ),
    'resources',
)

ICONS_PATH = os.path.join(
    RESOURCE_PATH,
    'icons',
)