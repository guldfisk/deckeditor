import itertools
import typing as t
from collections import defaultdict

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem

from magiccube.collections import cubeable as Cubeable
from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.components.views.cubeedit.graphical.alignment.aligner import Aligner
from deckeditor.components.views.cubeedit.graphical.physicalcard import PhysicalCard
from deckeditor.components.views.cubeedit.graphical.selection import SelectionScene
from deckeditor.models.deck import CubeModel
from deckeditor import values


class CubeScene(SelectionScene):

    def __init__(self, cube_model: CubeModel, aligner_type: t.Optional[t.Type[Aligner]] = None):
        super().__init__()
        self._cube_model = cube_model

        self.setSceneRect(0, 0, values.IMAGE_WIDTH * 12, values.IMAGE_HEIGHT * 8)

        self._aligner = (
            None
            if aligner_type is None else
            aligner_type(self)
        )

        self._item_map: t.MutableMapping[Cubeable, t.List[QGraphicsItem]] = defaultdict(list)

        self._update(
            CubeDeltaOperation(
                cube_model.cube.cubeables.elements()
            )
        )
        self._cube_model.changed.connect(self._update)

    def set_aligner(self, aligner_type: t.Type[Aligner]) -> None:
        cards = list(
            itertools.chain(
                *self._item_map.values()
            )
        )
        self.pick_up(cards)
        self._aligner = aligner_type(self)
        for card in cards:
            self.drop((card,), card.pos())

    def pick_up(self, items: t.Iterable[PhysicalCard]) -> None:
        if self._aligner is not None:
            self._aligner.pick_up(items)

    def drop(self, items: t.Iterable[PhysicalCard], position: QPoint) -> None:
        if self._aligner is not None:
            self._aligner.drop(items, position)

    def add_cubeable(self, cubeable: Cubeable) -> None:
        physical_card = PhysicalCard(cubeable)
        self._item_map[cubeable].append(physical_card)
        self.addItem(physical_card)
        self.drop([physical_card], physical_card.pos())

    def remove_cubeable(self, cubeable: Cubeable) -> None:
        physical_card = self._item_map[cubeable].pop()
        self.pick_up([physical_card])
        self.removeItem(physical_card)

    def _update(self, delta_operation: CubeDeltaOperation) -> None:
        for cubeable, multiplicity in delta_operation.removed_cubeables:
            for _ in range(-multiplicity):
                self.remove_cubeable(cubeable)

        for cubeable, multiplicity in delta_operation.new_cubeables:
            for _ in range(multiplicity):
                self.add_cubeable(cubeable)

