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
from deckeditor.models.deck import Deck


class _DeckSerializerMeta(ABCMeta):

    extension_to_serializer: t.Mapping[str, DeckSerializer] = {}

    def __new__(mcs, classname, base_classes, attributes):
        klass = type.__new__(mcs, classname, base_classes, attributes)
        print('deck serializer meta', classname, base_classes, attributes)

        if 'extensions' in attributes:
            for extension in attributes['extensions']:
                mcs.extension_to_serializer[extension] = klass

        return klass


class DeckSerializer(object, metaclass=_DeckSerializerMeta):

    extensions: t.Sequence[str]

    @classmethod
    @abstractmethod
    def serialize(cls, deck: Deck) -> t.AnyStr:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, s: t.AnyStr) -> Deck:
        pass


class DecSerializer(DeckSerializer):
    extensions = ['dec', 'mwDeck']

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


class JsonSerializer(DeckSerializer):
    extensions = ['json', 'JSON', 'embd']

    @classmethod
    def serialize(cls, deck: Deck) -> t.AnyStr:
        return JsonId.serialize(deck)

    @classmethod
    def deserialize(cls, s: t.AnyStr) -> Deck:
        return JsonId(Context.db).deserialize(Deck, s)
