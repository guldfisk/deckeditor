import typing as t

from collections import OrderedDict

from deckeditor.context.context import Context
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
    return ALIGNER_TYPE_MAP[Context.settings.value('default_aligner_type', DEFAULT_ALIGNER.name, str)]
