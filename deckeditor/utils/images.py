import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore


class ScaledImageLabel(QtWidgets.QLabel):

    def __init__(self, *args):
        super().__init__(*args)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self._pixmap: t.Optional[QtGui.QPixmap] = None

    @property
    def pixmap(self) -> QtGui.QPixmap:
        return self._pixmap

    def setPixmap(self, pixmap: QtGui.QPixmap):
        self._pixmap = pixmap
        super().setPixmap(self._scaled_pixmap())

    def heightForWidth(self, width: int) -> int:
        return (
            self.height()
            if self._pixmap is None else
            int(self._pixmap.height() * width / self._pixmap.width())
        )

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            self.width(),
            self.heightForWidth(self.width())
        )

    def _scaled_pixmap(self) -> QtGui.QPixmap:
        return self._pixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

    def resizeEvent(self, resize_event: QtGui.QResizeEvent):
        if not self._pixmap is None:
            super().setPixmap(self._scaled_pixmap())
