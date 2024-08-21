from __future__ import annotations

import typing as t

import sqlalchemy_jsonfield
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, update
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from deckeditor.sorting import sorting
from deckeditor.sorting.sorting import (
    DimensionContinuity,
    SortDimension,
    SortDirection,
    SortProperty,
)
from deckeditor.store import EDB
from deckeditor.store.fields import SortPropertyField


Base = declarative_base()


class GameTypeOptions(Base):
    __tablename__ = "game_type_options"

    id = Column(Integer, primary_key=True)
    game_type = Column(String(127), unique=True)
    options = Column(sqlalchemy_jsonfield.JSONField())

    @classmethod
    def save_options(cls, game_type: str, options: t.Mapping[str, t.Any]) -> None:
        try:
            EDB.Session.add(cls(game_type=game_type, options=options))
            EDB.Session.commit()
        except IntegrityError:
            EDB.Session.rollback()
            EDB.Session.execute(update(cls).where(cls.game_type == game_type).values(options=options))
            EDB.Session.commit()

    @classmethod
    def get_options_for_game_type(cls, game_type: str) -> t.Optional[t.Mapping[str, t.Any]]:
        instance = EDB.Session.query(cls.options).filter(cls.game_type == game_type).first()
        if instance is None:
            return instance
        return instance.options


class LobbyOptions(Base):
    __tablename__ = "lobby_options"

    id = Column(Integer, primary_key=True)
    name = Column(String(127), unique=True)
    options = Column(sqlalchemy_jsonfield.JSONField())

    @classmethod
    def save_options(cls, name: str, options: t.Mapping[str, t.Any]) -> None:
        try:
            EDB.Session.add(cls(name=name, options=options))
            EDB.Session.commit()
        except IntegrityError:
            EDB.Session.rollback()
            EDB.Session.execute(update(cls).where(cls.name == name).values(options=options))
            EDB.Session.commit()

    @classmethod
    def get_options_for_name(cls, name: str) -> t.Optional[t.Mapping[str, t.Any]]:
        instance = EDB.Session.query(cls.options).filter(cls.name == name).first()
        if instance is None:
            return instance
        return instance.options


class SortSpecification(Base, sorting.SortSpecification):
    __tablename__ = "sort_specification"

    id = Column(Integer, primary_key=True)

    index = Column(Integer)

    dimension: SortDimension = Column(Enum(SortDimension))
    direction: SortDirection = Column(Enum(SortDirection))
    sort_property: t.Type[SortProperty] = Column(SortPropertyField(63))

    respect_custom = Column(Boolean, default=True)

    macro_id = Column(
        Integer,
        ForeignKey("sort_macro.id", ondelete="CASCADE"),
        nullable=False,
    )
    macro: SortMacro = relationship("SortMacro", back_populates="specifications")


class SortMacro(Base, sorting.SortMacro):
    __tablename__ = "sort_macro"

    id = Column(Integer, primary_key=True)

    index = Column(Integer)
    name = Column(String(127))

    specifications: t.Sequence[SortSpecification] = relationship(
        "SortSpecification",
        back_populates="macro",
        cascade="all, delete-orphan",
        order_by=SortSpecification.index,
    )

    horizontal_continuity: DimensionContinuity = Column(Enum(DimensionContinuity), default=DimensionContinuity.AUTO)
    vertical_continuity: DimensionContinuity = Column(Enum(DimensionContinuity), default=DimensionContinuity.AUTO)
    sub_continuity: DimensionContinuity = Column(Enum(DimensionContinuity), default=DimensionContinuity.AUTO)


def create(engine: Engine):
    Base.metadata.create_all(engine)
