from __future__ import annotations

import os
import typing as t

from magiccube.collections.infinites import Infinites
from mtgorp.models.serilization.strategies.raw import RawStrategy
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon

from deckeditor import paths
from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options.selector import OptionsSelector
from deckeditor.context.context import Context
from deckeditor.utils.containers.cardboardlist import CardboardList
from deckeditor.utils.stack import DynamicSizeStack
from deckeditor.views.focusables.dialogs import SelectCardboardDialog


class InfinitesSummary(QtWidgets.QLabel, OptionsSelector):
    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        self.setText(
            ", ".join(
                sorted(
                    c.name
                    for c in RawStrategy(Context.db).deserialize(
                        Infinites,
                        options["infinites"],
                    )
                )
            )
        )


class InfinitesTable(CardboardList):
    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__()
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        self._lobby_view = lobby_view

        self._enabled = True

        self._infinites = Infinites()

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        pressed_key = key_event.key()

        if pressed_key == QtCore.Qt.Key_Delete and self._enabled:
            item = self.currentItem()
            if item is not None:
                self._lobby_view.lobby_model.set_options(
                    self._lobby_view.lobby.name,
                    {
                        "infinites": RawStrategy.serialize(
                            self._infinites - Infinites((Context.db.cardboards[item.data(0)],))
                        ),
                    },
                )
        else:
            super().keyPressEvent(key_event)

    def update_content(self, infinites: Infinites, enabled: bool) -> None:
        self._enabled = enabled
        self._infinites = infinites
        self.set_cardboards(infinites)


class InfinitesSelector(QtWidgets.QWidget, OptionsSelector):
    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__()

        self._lobby_view = lobby_view
        self._infinites = Infinites()

        self._toggle_button = QtWidgets.QPushButton()
        self._toggle_button.setFixedSize(QSize(20, 20))
        self._toggle_button.setIcon(QIcon(os.path.join(paths.ICONS_PATH, "maximize.svg")))

        self._expanded = False

        self._toggle_button.pressed.connect(self._handle_toggle)

        self._add_button = QtWidgets.QPushButton()
        self._add_button.setFixedSize(QSize(20, 20))
        self._add_button.setIcon(QIcon(os.path.join(paths.ICONS_PATH, "plus.svg")))

        self._add_button.pressed.connect(self._handle_add)

        self._summary = InfinitesSummary()
        self._table = InfinitesTable(self._lobby_view)

        self._stack = DynamicSizeStack()
        self._stack.addWidget(self._summary)
        self._stack.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum)
        self._stack.addWidget(self._table)
        self._stack.setCurrentWidget(self._summary)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._stack)
        layout.addWidget(self._toggle_button, alignment=QtCore.Qt.AlignTop)
        layout.addWidget(self._add_button, alignment=QtCore.Qt.AlignTop)

    def _handle_toggle(self) -> None:
        self._expanded = not self._expanded
        self._toggle_button.setIcon(
            QIcon(os.path.join(paths.ICONS_PATH, "minimize.svg" if self._expanded else "maximize.svg"))
        )
        self._stack.setCurrentWidget(self._table if self._expanded else self._summary)

    def _handle_add(self) -> None:
        cardboard, accepted = SelectCardboardDialog.get_cardboard()

        if not accepted:
            return

        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {
                "infinites": RawStrategy.serialize(self._infinites + Infinites((cardboard,))),
            },
        )

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        self._summary.update_content(options, enabled)
        self._infinites = RawStrategy(Context.db).deserialize(Infinites, options["infinites"])
        self._table.update_content(self._infinites, enabled)
        self._add_button.setEnabled(enabled)
