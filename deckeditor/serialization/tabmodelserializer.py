from __future__ import annotations

import types
import typing as t

from abc import abstractmethod, ABCMeta

from mtgorp.models.serilization.strategies.jsonid import JsonId
from mtgorp.tools import deckio

from deckeditor.context.context import Context
from deckeditor.models.deck import Deck, TabModel, Pool


T = t.TypeVar('T', bound = TabModel)


class _TabModelSerializerMeta(ABCMeta):
    extension_to_serializer: t.Mapping[t.Tuple[str, t.Type[T]], TabModelSerializer[T]] = {}

    def __new__(mcs, classname, base_classes, attributes):
        klass = type.__new__(mcs, classname, base_classes, attributes)

        if 'extensions' in attributes:
            for extension in attributes['extensions']:
                mcs.extension_to_serializer[(extension, attributes['tab_model_type'])] = klass

        return klass


class TabModelSerializer(t.Generic[T], metaclass = _TabModelSerializerMeta):
    extensions: t.Sequence[str]
    tab_model_type: t.Type[T]

    @classmethod
    @abstractmethod
    def serialize(cls, tab_model: TabModel) -> t.AnyStr:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, s: t.AnyStr) -> T:
        pass


def init_deck_serializers():
    for serializer_type in deckio.DecSerializer.extension_to_serializer.values():
        types.new_class(
            '_' + serializer_type.__name__,
            (TabModelSerializer[Deck],),
            {'metaclass': _TabModelSerializerMeta},
            lambda d: d.update(
                {
                    'extensions': serializer_type.extensions,
                    'tab_model_type': Deck,
                    '_serializer': serializer_type(Context.db),
                    'serialize': classmethod(
                        lambda cls, tab_model: cls._serializer.serialize(tab_model.as_primitive_deck())
                    ),
                    'deserialize': classmethod(
                        lambda cls, s: Deck.from_primitive_deck(cls._serializer.deserialize(s))
                    ),
                }
            ),
        )


class PoolJsonSerializer(TabModelSerializer[Pool]):
    extensions = ['json', 'JSON']
    tab_model_type = Pool

    @classmethod
    def serialize(cls, pool: Pool) -> t.AnyStr:
        return JsonId.serialize(pool)

    @classmethod
    def deserialize(cls, s: t.AnyStr) -> Pool:
        return JsonId(Context.db).deserialize(Pool, s)
