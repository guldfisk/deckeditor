import typing as t
from abc import abstractmethod

from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable


class MultiCubesView(Editable):

    @property
    @abstractmethod
    def cube_views(self) -> t.Iterable[CubeView]:
        pass

    @property
    def cube_views_map(self):
        return {
            view.cube_scene.name: view
            for view in
            self.cube_views
        }
