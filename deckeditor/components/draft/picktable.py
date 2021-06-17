from __future__ import annotations

from hardcandy import fields
from hardcandy.schema import Schema

from mtgdraft.models import PickPoint, SinglePickPick, BurnPick

from deckeditor.components.cardview.focuscard import describe_focusable


class PickTableSchema(Schema[PickPoint]):
    global_pick_number = fields.Integer()
    pack_number = fields.Lambda(lambda p: p.round.pack)
    pick_number = fields.Integer()
    pick = fields.Lambda(lambda p: describe_focusable(p.pick.cubeable if isinstance(p.pick, SinglePickPick) else p.pick.pick))
    burn = fields.Lambda(lambda p: describe_focusable(p.pick.burn) if isinstance(p.pick, BurnPick) and p.pick.burn is not None else '')
    pack = fields.Lambda(
        lambda p: ', '.join(
            map(
                describe_focusable,
                p.booster.cubeables,
            )
        )
    )

# class _LinesProxy(t.Sequence[PickPoint]):
#
#     def __init__(self, filter_model: PickPointFilterModel) -> None:
#         self._filter_model = filter_model
#
#     def __getitem__(self, i: int) -> PickPoint:
#         self._filter_model.sourceModel()
#
#     def __len__(self) -> int:
#         raise NotImplemented()


# class PickPointFilterModel(QSortFilterProxyModel):
#     sourceModel: t.Callable[[], ListTableModel[PickPoint]]
#
#     def __init__(self) -> None:
#         super().__init__()
#         self._filter: t.Optional[PrintingPattern] = None
#
#     @property
#     def lines(self) -> t.Sequence[PickPoint]:
#         self.cubeable_double_clicked.emit(self.model().sourceModel().items_at(self.model().mapToSource(index).row())[0])
#
#     def set_filter(self, printing_filter: PrintingPattern) -> None:
#         self._filter = printing_filter
#
#     def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
#         if self._filter is None:
#             return True
#         pp = self.sourceModel().lines[source_row]
#         return any(match_cubeable(self._filter, itertools.chain(pp.pick.picked, pp.booster.cubeables)))
