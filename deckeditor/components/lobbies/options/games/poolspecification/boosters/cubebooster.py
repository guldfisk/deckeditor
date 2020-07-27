import itertools
import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.games.poolspecification.interface import BoosterSpecificationSelectorInterface
from deckeditor.components.lobbies.options.release import ReleaseSelector
from deckeditor.components.lobbies.options.primitives import IntegerOptionSelector
from deckeditor.context.context import Context


class CubeBoosterSpecificationSelector(QtWidgets.QWidget):

    def __init__(
        self,
        lobby_view: LobbyViewInterface,
        booster_specification_selector: BoosterSpecificationSelectorInterface,
    ):
        super().__init__()

        self._booster_specification_selector = booster_specification_selector

        self._release_selector = ReleaseSelector(lobby_view)
        self._size_selector = IntegerOptionSelector(lobby_view, allowed_range = (1, 360))
        self._allow_intersection_selector = QtWidgets.QCheckBox('Allow Intersections')
        self._allow_repeat_selector = QtWidgets.QCheckBox('Allow Repeats')
        self._scale = QtWidgets.QCheckBox('scale')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)

        layout.addWidget(self._release_selector, Qt.AlignTop)
        layout.addWidget(self._size_selector, Qt.AlignTop)

        flags_grid = QtWidgets.QGridLayout()

        flags_grid.addWidget(self._allow_intersection_selector, 0, 0, 1, 1)
        flags_grid.addWidget(self._allow_repeat_selector, 0, 1, 1, 1)
        flags_grid.addWidget(self._scale, 1, 0, 1, 1)

        layout.addLayout(flags_grid, Qt.AlignTop)
        layout.addStretch()

        self._size_selector.valueChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit('size', v)
        )
        self._release_selector.release_selected.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit('release', v)
        )
        self._allow_intersection_selector.stateChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                'allow_intersection',
                v == 2,
            )
        )
        self._allow_repeat_selector.stateChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                'allow_repeat',
                v == 2,
            )
        )
        self._scale.stateChanged.connect(
            lambda v: self._booster_specification_selector.booster_specification_value_changed.emit(
                'scale',
                v == 2,
            )
        )

    def get_default_values(self) -> t.Mapping[str, t.Any]:
        return {
            'type': 'CubeBoosterSpecification',
            'release': sorted(
                itertools.chain(
                    *(
                        versioned_cube.releases
                        for versioned_cube in
                        Context.cube_api_client.versioned_cubes().get()
                    )
                ),
                key = lambda release: release.created_at,
            )[-1].id,
            'size': 90,
            'allow_intersection': False,
            'allow_repeat': False,
            'scale': False,
            'amount': 1,
        }

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._release_selector.update_content(specification['release'], enabled)
        self._size_selector.update_content(specification['size'], enabled)

        self._allow_intersection_selector.blockSignals(True)
        self._allow_intersection_selector.setEnabled(enabled)
        self._allow_intersection_selector.setChecked(specification['allow_intersection'])
        self._allow_intersection_selector.blockSignals(False)

        self._allow_repeat_selector.blockSignals(True)
        self._allow_repeat_selector.setEnabled(enabled)
        self._allow_repeat_selector.setChecked(specification['allow_repeat'])
        self._allow_repeat_selector.blockSignals(False)

        self._scale.blockSignals(True)
        self._scale.setEnabled(enabled)
        self._scale.setChecked(specification['scale'])
        self._scale.blockSignals(False)
