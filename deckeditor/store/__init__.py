from sqlalchemy import create_engine
from sqlalchemy.orm.session import sessionmaker, Session as _Session
from sqlalchemy.orm import scoped_session

from deckeditor import paths


engine = create_engine(f'sqlite:///{paths.DB_PATH}')

session_factory = sessionmaker(bind = engine)
Session: _Session = scoped_session(session_factory)
