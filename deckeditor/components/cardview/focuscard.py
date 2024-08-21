import typing as t
from dataclasses import dataclass

from magiccube.collections.cubeable import CardboardCubeable, Cubeable
from mtgorp.models.interfaces import Cardboard, Printing


Focusable = t.Union[Cubeable, Cardboard]


def describe_focusable(focusable: Focusable) -> str:
    if isinstance(focusable, Cardboard):
        return focusable.name
    if isinstance(focusable, Printing):
        return focusable.cardboard.name
    return focusable.description


def focusable_as_cardboards(focusable: Focusable) -> CardboardCubeable:
    if isinstance(focusable, Cardboard):
        return focusable
    if isinstance(focusable, Printing):
        return focusable.cardboard
    return focusable.as_cardboards


@dataclass
class FocusEvent(object):
    focusable: Focusable
    size: t.Optional[t.Tuple[float, float]] = None
    position: t.Optional[t.Tuple[float, float]] = None
    modifiers: t.Optional[int] = None
    back: bool = False
    release_id: t.Optional[int] = None
