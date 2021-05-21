from __future__ import annotations

import typing as t

from mtgorp.models.interfaces import Printing

from magiccube.laps.lap import Lap

from deckeditor.components.views.cubeedit.graphical.graphicpixmapobject import GraphicPixmapObject


C = t.TypeVar('C', bound = t.Union[Printing, Lap])


class SceneCard(GraphicPixmapObject, t.Generic[C]):
    _cubeable: C
    values: t.Optional[t.MutableMapping[str, t.Any]]

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
