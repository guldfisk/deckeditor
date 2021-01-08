import typing as t

from collections import OrderedDict

from deckeditor.components.settings import settings
from deckeditor.models.cubes.alignment.aligner import Aligner
from deckeditor.models.cubes.alignment.bunchingstackinggrid import BunchingStackingGrid
from deckeditor.models.cubes.alignment.dynamicstackinggrid import DynamicStackingGrid
from deckeditor.models.cubes.alignment.grid import GridAligner
from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid


ALIGNER_TYPE_MAP = OrderedDict(
    (
        (aligner.name, aligner)
        for aligner in (
            StaticStackingGrid,
            GridAligner,
            BunchingStackingGrid,
            DynamicStackingGrid,
        )
    )
)


DEFAULT_ALIGNER = DynamicStackingGrid


def get_default_aligner_type() -> t.Type[Aligner]:
    return ALIGNER_TYPE_MAP[settings.DEFAULT_ALIGNER_TYPE.get_value()]
