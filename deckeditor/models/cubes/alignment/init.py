from deckeditor.models.cubes.alignment.aligners import ALIGNER_TYPE_MAP
from deckeditor.models.cubes.alignment.bunchingstackinggrid import BunchingStackingGrid
from deckeditor.models.cubes.alignment.dynamicstackinggrid import DynamicStackingGrid
from deckeditor.models.cubes.alignment.grid import GridAligner
from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid


def init_aligners() -> None:
    for aligner in (
        DynamicStackingGrid,
        GridAligner,
        BunchingStackingGrid,
        StaticStackingGrid,
    ):
        ALIGNER_TYPE_MAP[aligner.name] = aligner
