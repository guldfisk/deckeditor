from __future__ import annotations

import typing as t

from collections import OrderedDict

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from mtgorp.models.persistent.attributes.colors import Color


class SingleInstanceDialog(QDialog):
    INSTANCE: t.Optional[SingleInstanceDialog] = None

    @classmethod
    def get(cls) -> SingleInstanceDialog:
        if cls.INSTANCE is None:
            cls.INSTANCE = cls()
        return cls.INSTANCE


class ColorSelector(QDialog):
    color_selected = pyqtSignal(object)

    def __init__(self, colors: t.Optional[t.AbstractSet[Color]] = None, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._has_been_accepted = False

        layout = QtWidgets.QVBoxLayout(self)

        self._check_boxes = OrderedDict(
            (color, QtWidgets.QCheckBox())
                for color in
                Color
        )

        if colors is not None:
            for color in colors:
                self._check_boxes[color].setChecked(True)

        colors_layout = QtWidgets.QFormLayout()

        for color, check_box in self._check_boxes.items():
            colors_layout.addRow(color.letter_code, check_box)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        self.accepted.connect(self._set_has_been_accepted)

        layout.addLayout(colors_layout)
        layout.addWidget(self._buttons)

    @property
    def colors(self):
        return frozenset(
            color
                for color, check_box in
                self._check_boxes.items()
                if check_box.isChecked()
        )

    def _set_has_been_accepted(self) -> None:
        self._has_been_accepted = True

    @classmethod
    def get_colors(
        cls,
        color: t.Optional[t.AbstractSet[Color]] = None,
    ) -> t.Tuple[t.Optional[t.FrozenSet[Color]], bool]:
        dialog = cls(color)
        dialog.exec()
        if dialog._has_been_accepted:
            return dialog.colors, True
        else:
            return None, False
