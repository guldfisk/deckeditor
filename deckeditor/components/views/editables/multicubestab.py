import typing as t

from abc import abstractmethod

from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable


class MultiCubesTab(Editable):

    @property
    @abstractmethod
    def cube_views(self) -> t.Iterable[CubeView]:
        pass
