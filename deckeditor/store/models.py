from __future__ import annotations

import collections
import typing as t

from sqlalchemy import Integer, String, Column, update
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base

import sqlalchemy_jsonfield

from deckeditor.store import Session


Base = declarative_base()


class GameTypeOptions(Base):
    __tablename__ = 'game_type_options'

    id = Column(Integer, primary_key = True)
    game_type = Column(String, unique = True)
    options = Column(sqlalchemy_jsonfield.JSONField())

    @classmethod
    def save_options(cls, game_type: str, options: t.Mapping[str, t.Any]) -> None:
        try:
            Session.add(cls(game_type = game_type, options = options))
            Session.commit()
        except IntegrityError:
            Session.rollback()
            Session.execute(update(cls).where(cls.game_type == game_type).values(options = options))
            Session.commit()

    @classmethod
    def get_options_for_game_type(cls, game_type: str) -> t.Optional[t.Mapping[str, t.Any]]:
        instance = Session.query(cls.options).filter(cls.game_type == game_type).first()
        if instance is None:
            return instance
        return instance.options


class LobbyOptions(Base):
    __tablename__ = 'lobby_options'

    id = Column(Integer, primary_key = True)
    name = Column(String, unique = True)
    options = Column(sqlalchemy_jsonfield.JSONField())

    @classmethod
    def save_options(cls, name: str, options: t.Mapping[str, t.Any]) -> None:
        try:
            Session.add(cls(name = name, options = options))
            Session.commit()
        except IntegrityError:
            Session.rollback()
            Session.execute(update(cls).where(cls.name == name).values(options = options))
            Session.commit()

    @classmethod
    def get_options_for_name(cls, name: str) -> t.Optional[t.Mapping[str, t.Any]]:
        instance = Session.query(cls.options).filter(cls.name == name).first()
        if instance is None:
            return instance
        return instance.options


# class SortSpecification(Base):
#     __tablename__ = 'sort_specification'
#
#     id = Column(Integer, primary_key = True)
#
#     index = Column(Integer)
#
#     dimension: SortDimension = Column(Enum(SortDimension))
#     direction: SortDirection = Column(Enum(SortDirection))
#     sort_property = Column(String)
#
#     respect_custom = Column(Boolean, default = True)
#
#     macro: SortMacro = relationship('SortMacro', back_populates = 'specifications')
#
#
# class SortMacro(Base):
#     __tablename__ = 'sort_macro'
#
#     id = Column(Integer, primary_key = True)
#
#     specifications: t.Sequence[SortSpecification] = relationship(
#         'SortSpecification',
#         back_populates = 'macro',
#         cascade = 'all, delete-orphan',
#     )
#
#     @property
#     def dimension_specifications_map(self) -> t.Sequence[t.Tuple[SortDimension, t.Sequence[SortSpecification]]]:
#         _map = collections.defaultdict(list)
#         for specification in self.specifications:
#             _map[specification.dimension].append(specification)
#
#         return sorted(
#             (
#                 (dimension, sorted(specifications, key = lambda s: s.index))
#                 for dimension, specifications in
#                 _map.items()
#             ),
#             key = lambda p: p[0],
#         )


def create(engine: Engine):
    Base.metadata.create_all(engine)
