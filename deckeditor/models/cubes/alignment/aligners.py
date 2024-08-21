import typing as t
from collections import OrderedDict

from deckeditor.components.settings import settings
from deckeditor.models.cubes.alignment.aligner import Aligner
from deckeditor.models.cubes.scenetypes import SceneType


ALIGNER_TYPE_MAP: t.OrderedDict[str, t.Type[Aligner]] = OrderedDict()


def get_default_aligner_type(scene_type: SceneType) -> t.Type[Aligner]:
    return ALIGNER_TYPE_MAP[settings.SCENE_DEFAULTS.get_value()[scene_type.value]["aligner_type"]]
