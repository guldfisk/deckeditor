import typing as t
from abc import abstractmethod

from deckeditor.components.views.cubeedit.cubeview import CubeView
from deckeditor.components.views.editables.editable import Editable
from deckeditor.models.cubes.scenetypes import SceneType


class MultiCubesView(Editable):
    @property
    @abstractmethod
    def cube_views(self) -> t.Iterable[CubeView]:
        pass

    @property
    def cube_views_map(self) -> t.Mapping[SceneType, CubeView]:
        return {view.cube_scene.scene_type: view for view in self.cube_views}
