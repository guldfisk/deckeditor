from __future__ import annotations

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QGraphicsScene


class GraphicsMiniView(QtWidgets.QGraphicsView):
    def __init__(self):
        super().__init__()

        self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

    def set_scene(self, scene: QGraphicsScene):
        if scene == self.scene():
            return
        self.setScene(scene)
        self.fitInView(
            self.scene().sceneRect(),
            QtCore.Qt.KeepAspectRatio,
        )
