import typing as t

from PyQt5.QtCore import QPoint

from deckeditor.components.views.cubeedit.graphical.selection import SelectionScene
from deckeditor.values import IMAGE_WIDTH, IMAGE_HEIGHT
from mtgimg.interface import SizeSlug

from deckeditor.components.views.cubeedit.graphical.alignment.aligner import Aligner
from deckeditor.garbage.cardcontainers.physicalcard import PhysicalCard


class GridAligner(Aligner):

    def __init__(self, scene: SelectionScene, margin: int = 10, columns: t.Optional[int] = None):
        super().__init__(scene)

        self._margin = margin
        self._columns = self._scene.width() // (IMAGE_WIDTH + self._margin) if columns is None else columns

        self._cards: t.List[PhysicalCard] = []

    def pick_up(self, items: t.Iterable[PhysicalCard]) -> None:
        minimum_index = len(self._cards) - 1

        for item in items:
            idx = self._cards.index(item)
            self._cards.pop(idx)
            minimum_index = min(minimum_index, idx)

        self.realign(minimum_index)

        for card in items:
            card.setZValue(1)

    def get_position_at_index(self, idx: int) -> QPoint:
        return QPoint(
            max(
                min(
                    (idx % self._columns) * (IMAGE_WIDTH + self._margin),
                    self._scene.width() - IMAGE_WIDTH
                ),
                0
            ),
            max(
                min(
                    (idx // self._columns) * (IMAGE_HEIGHT + self._margin),
                    self._scene.height() - IMAGE_HEIGHT
                ),
                0
            ),
        )

    def map_position_to_index(self, position: QPoint) -> int:
        return int(
            position.x() // (SizeSlug.ORIGINAL.get_size(False)[0] + self._margin)
            + (position.y() // (SizeSlug.ORIGINAL.get_size(False)[1] + self._margin) * self._columns
               )
        )

    def realign(self, from_index: int) -> None:
        for card, idx in zip(self._cards[from_index:], range(from_index, len(self._cards))):
            card.setPos(
                self.get_position_at_index(
                    idx
                )
            )

    def drop(self, items: t.Iterable[PhysicalCard], position: QPoint) -> None:
        drop_idx = self.map_position_to_index(position)
        self._cards[drop_idx:drop_idx] = list(items)
        self.realign(drop_idx)
        for card in items:
            card.setZValue(0)
