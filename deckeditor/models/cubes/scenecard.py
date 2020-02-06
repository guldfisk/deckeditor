from __future__ import annotations

import typing as t

from deckeditor.components.views.cubeedit.graphical.graphicpixmapobject import GraphicPixmapObject
from magiccube.laps.lap import Lap
from mtgorp.models.persistent.printing import Printing


C = t.TypeVar('C', bound = t.Union[Printing, Lap])


class SceneCard(GraphicPixmapObject, t.Generic[C]):
    _cubeable: C

    @property
    def cubeable(self) -> C:
        return self._cubeable

    @classmethod
    def from_cubeable(cls, cubeable: C, node_parent: t.Optional[SceneCard] = None) -> SceneCard[C]:
        pass

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            self.cubeable,
        )
