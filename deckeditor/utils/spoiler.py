from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal


class ClickableFrame(QtWidgets.QFrame):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(a0)
        self.clicked.emit()


class Spoiler(QtWidgets.QWidget):

    def __init__(self, expanded: bool = True):
        super().__init__()

        self._expanded = expanded

        self._header_line = ClickableFrame()
        self._header_line.setFrameShape(QtWidgets.QFrame.HLine)
        self._header_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self._header_line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

        self._content_area = QtWidgets.QScrollArea()
        self._content_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._content_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self._content_area.setMaximumHeight(0)
        self._content_area.setMinimumHeight(0)

        self._main_layout = QtWidgets.QGridLayout(self)
        self._main_layout.setVerticalSpacing(0)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.addWidget(self._header_line, 0, 0)
        self._main_layout.addWidget(self._content_area, 1, 0)

        self._header_line.clicked.connect(self.toggle_expanded)

    @property
    def expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        collapsed_height = self._header_line.sizeHint().height()
        content_height = self._content_area.layout().sizeHint().height()
        if self._expanded:
            self.setMinimumHeight(collapsed_height + content_height)
            self.setMaximumHeight(collapsed_height + content_height)
            self._content_area.setMaximumHeight(content_height)
        else:
            self.setMaximumHeight(collapsed_height)
            self.setMinimumHeight(collapsed_height)
            self._content_area.setMaximumHeight(0)

    def toggle_expanded(self) -> None:
        self.set_expanded(not self._expanded)

    def set_content_layout(self, layout: QtWidgets.QLayout):
        self._content_area.setLayout(layout)
        self.set_expanded(self._expanded)
