import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QUndoStack

from deckeditor.models.cubes.alignment.aligner import Aligner
from deckeditor.models.cubes.alignment.grid import GridAligner
from deckeditor.models.cubes.alignment.staticstackinggrid import StaticStackingGrid
from deckeditor.components.views.cubeedit.graphical.cubeimageview import CubeImageView
from deckeditor.models.cubes.cubescene import CubeScene

from deckeditor.context.context import Context

ALIGNER_TYPE_MAP = {
    'Grid': GridAligner,
    'Static Stacking Grid': StaticStackingGrid,
    # 'Dynamic Stacking Grid': DynamicStackingGrid,
}


# class ChangeAligner(UndoCommand):
#
#     def __init__(self, deck_zone_widget: 'DeckZone', aligner: Aligner):
#         self._deck_zone_widget = deck_zone_widget
#         self._scene = deck_zone_widget.card_container.card_scene
#         self._aligner = aligner
#         self._previous_aligner = None #type: t.Optional[Aligner]
#         self._cards = [] #type: t.List[PhysicalCard]
#         self._detach = None #type: UndoCommand
#         self._attach = None #type: UndoCommand
#
#     def setup(self):
#         self._previous_aligner = self._scene.aligner
#         self._cards = list(self._scene.cards)
#
#         self._detach = self._scene.aligner.detach_cards(self._cards)
#         self._detach.setup()
#
#         self._attach = self._aligner.attach_cards(self._cards, QtCore.QPointF(0, 0))
#         self._attach.setup()
#
#     def redo(self) -> None:
#         if not self._detach.ignore():
#             self._detach.redo()
#         self._deck_zone_widget.aligner_changed.emit(self._aligner)
#         if not self._attach.ignore():
#             self._attach.redo()
#
#     def undo(self) -> None:
#         if not self._attach.ignore():
#             self._attach.undo()
#         self._deck_zone_widget.aligner_changed.emit(self._previous_aligner)
#         if not self._detach.ignore():
#             self._detach.undo()


class SelectedInfo(QtWidgets.QLabel):

    def set_amount_selected(self, selected: int = 0):
        self.setText(f'{selected} selected items')


class AlignSelector(QtWidgets.QComboBox):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        for name, aligner_type in ALIGNER_TYPE_MAP.items():
            self.addItem(name, aligner_type)

        self.setCurrentIndex(
            self.findData(StaticStackingGrid)
        )

    def change_current_item(self, aligner: Aligner) -> None:
        if aligner != self.currentData():
            self.setCurrentIndex(
                self.findData(
                    type(aligner)
                )
            )


class CubeMultiImageView(QtWidgets.QWidget):
    aligner_changed = QtCore.pyqtSignal(type)

    def __init__(self, scene: CubeScene, undo_stack: QUndoStack, parent = None):
        super().__init__(parent = parent)

        self._cube_scene = scene

        # self._undo_stack = undo_stack

        self._current_aligner_type = StaticStackingGrid

        self._cube_image_view = CubeImageView(
            undo_stack,
            self._cube_scene
        )

        self._cube_scene.set_aligner(
            self._current_aligner_type
        )

        # self._card_container = CardContainer(
        #     self._undo_stack,
        #     self._current_aligner_type,
        # )
        # self._selected_info = SelectedInfo()
        self._aligner_selector = AlignSelector(self)

        # self._zone_label.setText(self._zone.value)

        # self._card_container.scene().selectionChanged.connect(self.selection_change)

        default_scale = Context.settings.value('default_card_view_scale', .2, float)
        # self._cube_scene.setScale(default_scale, default_scale)

        box = QtWidgets.QVBoxLayout(self)

        self._tool_bar = QtWidgets.QHBoxLayout(self)

        # self._tool_bar.addWidget(self._zone_label)
        # self._tool_bar.addWidget(self._selected_info)
        self._tool_bar.addWidget(self._aligner_selector)

        # self._selected_info.set_amount_selected()

        box.addLayout(self._tool_bar)
        box.addWidget(self._cube_image_view)

        self.setLayout(box)

        self.aligner_changed.connect(self._aligner_changed)
        self.aligner_changed.connect(self._aligner_selector.change_current_item)
        self._aligner_selector.currentIndexChanged.connect(self._combo_box_changed)

    def _aligner_changed(self, aligner: t.Type[Aligner]) -> None:
        self._cube_scene.set_aligner(aligner)
        self._current_aligner_type = aligner

    def _combo_box_changed(self, index: int) -> None:
        aligner_type = self._aligner_selector.itemData(index)

        if aligner_type == self._current_aligner_type:
            return

        self.aligner_changed.emit(aligner_type)

        # self._undo_stack.push(
        #     ChangeAligner(
        #         self,
        #         aligner_type(
        #             self.card_container.scene(),
        #             self._undo_stack,
        #         ),
        #     )
        # )

    # def selection_change(self):
    #     self._selected_info.set_amount_selected(
    #         len(self._card_container.scene().selectedItems())
    #     )
    #
    # @property
    # def card_container(self) -> CardContainer:
    #     return self._card_container
    #
    # @property
    # def undo_stack(self) -> UndoStack:
    #     return self._undo_stack
    #
    # @property
    # def printings(self) -> t.Iterable[Printing]:
    #     return (card.cubeable for card in self._card_container.card_scene.cards)

