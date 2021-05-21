import typing as t
from dataclasses import dataclass

from mtgorp.models.interfaces import Cardboard, Printing

from magiccube.collections.cubeable import Cubeable, CardboardCubeable


Focusable = t.Union[Cubeable, Cardboard]


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
