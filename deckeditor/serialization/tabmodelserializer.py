from __future__ import annotations

import re
import typing as t

from abc import abstractmethod, ABCMeta

from mtgorp.models.serilization.strategies.jsonid import JsonId
from yeetlong.multiset import Multiset

from mtgorp.models.persistent.printing import Printing
from mtgorp.models.serilization.serializeable import SerializationException

from magiccube.collections.cube import Cube

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


class TabModelSerializer(t.Generic[T], metaclass=_TabModelSerializerMeta):

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


class DecSerializer(TabModelSerializer[Deck]):
    extensions = ['dec', 'mwDeck']
    tab_model_type = Deck

    _x_printings_pattern = re.compile('(SB:\s+)?(\d+) \[([A-Z0-9]*)\] (.*?)\s*$')

    @classmethod
    def _printings_to_line(cls, printing: Printing, multiplicity: int) -> str:
        return '{} [{}] {}'.format(
            multiplicity,
            printing.expansion.code,
            printing.cardboard.name.replace('//', '/'),
        )

    @classmethod
    def serialize(cls, deck: Deck) -> t.AnyStr:
        s = '// Deck file created with embargo edit'
        for printing, multiplicity in deck.maindeck.printings.items():
            s += '\n' + cls._printings_to_line(printing, multiplicity)
        for printing, multiplicity in deck.sideboard.printings.items():
            s += '\nSB:  ' + cls._printings_to_line(printing, multiplicity)
        return s + '\n'

    @classmethod
    def _get_printing(cls, name: str, expansion_code: str) -> Printing:
        try:
            try:
                cardboard = Context.db.cardboards[name]
            except KeyError:
                cardboard = Context.db.cards[name].cardboard
        except KeyError:
            raise SerializationException('invalid cardboard name "{}"'.format(name))
        try:
            return cardboard.from_expansion(expansion_code, allow_volatile = True)
        except KeyError:
            return cardboard.latest_printing

    @classmethod
    def deserialize(cls, s: t.AnyStr) -> Deck:
        maindeck = Multiset()
        sideboard = Multiset()
        for ln in s.split('\n'):
            m = cls._x_printings_pattern.match(ln)
            if m:
                (
                    sideboard
                    if m.group(1) else
                    maindeck
                ).add(
                    cls._get_printing(m.group(4).replace('/', '//'), m.group(3)),
                    int(m.group(2)),
                )

        return Deck(
            Cube(maindeck),
            Cube(sideboard),
        )


class DeckJsonSerializer(TabModelSerializer[Deck]):
    extensions = ['json', 'JSON']
    tab_model_type = Deck

    @classmethod
    def serialize(cls, deck: Deck) -> t.AnyStr:
        return JsonId.serialize(deck)

    @classmethod
    def deserialize(cls, s: t.AnyStr) -> Deck:
        return JsonId(Context.db).deserialize(Deck, s)


class PoolJsonSerializer(TabModelSerializer[Pool]):
    extensions = ['json', 'JSON']
    tab_model_type = Pool

    @classmethod
    def serialize(cls, deck: Deck) -> t.AnyStr:
        return JsonId.serialize(deck)

    @classmethod
    def deserialize(cls, s: t.AnyStr) -> Deck:
        return JsonId(Context.db).deserialize(Deck, s)
