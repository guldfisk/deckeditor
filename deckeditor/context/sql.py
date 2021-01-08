import typing as t

from PyQt5 import QtCore

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session

from orp.alchemy import patch_alchemy


class SqlContext(object):
    engine: Engine
    scoped_session: t.Callable[[], Session]

    @classmethod
    def init(cls, settings: QtCore.QSettings):
        uri = '{dialect}+{driver}://{username}:{password}@{host}/{database}?charset=utf8'.format(
            dialect = settings.value('sql_dialect', 'mysql', str),
            driver = settings.value('sql_driver', 'mysqldb', str),
            username = settings.value('sql_user', 'user', str),
            password = settings.value('sql_password', '', str),
            host = settings.value('sql_host', 'localhost', str),
            database = settings.value('sql_database', 'mtg', str),
        )

        cls.engine = create_engine(
            uri,
            pool_size = 64,
            max_overflow = 32,
        )

        session_factory = sessionmaker(bind = cls.engine)
        cls.scoped_session = scoped_session(session_factory)
        patch_alchemy(cls.scoped_session)
