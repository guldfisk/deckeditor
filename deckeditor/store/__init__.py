from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.session import Session as _Session
from sqlalchemy.orm.session import sessionmaker

from deckeditor import paths
from deckeditor.components.settings import settings


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class EDB(object):
    engine: Engine = None
    Session: _Session = None

    @classmethod
    def init(cls, echo: bool = False) -> None:
        cls.engine = (
            create_engine(f"sqlite:///{paths.DB_PATH}", echo=echo)
            if not settings.EXTERNAL_STORE_DB.get_value()
            else create_engine(
                "{dialect}+{driver}://{username}:{password}@{host}/{database}?charset=utf8".format(
                    dialect=settings.SQL_DIALECT.get_value(),
                    driver=settings.SQL_DRIVER.get_value(),
                    username=settings.SQL_USER.get_value(),
                    password=settings.SQL_PASSWORD.get_value(),
                    host=settings.SQL_HOST.get_value(),
                    database=settings.EXTERNAL_DATABASE_NAME.get_value(),
                ),
                pool_size=16,
                max_overflow=8,
            )
        )

        cls.Session = scoped_session(sessionmaker(bind=cls.engine))
