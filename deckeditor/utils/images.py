import typing as t

from PyQt5 import QtCore, QtGui, QtWidgets


class ScaledImageLabel(QtWidgets.QLabel):
    def __init__(self, *args):
        super().__init__(*args)
        self.setMinimumSize(1, 1)
        self.setScaledContents(False)
        self._pixmap: t.Optional[QtGui.QPixmap] = None

        self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)

    @property
    def pixmap(self) -> QtGui.QPixmap:
        return self._pixmap

    def setPixmap(self, pixmap: QtGui.QPixmap):
        self._pixmap = pixmap
        super().setPixmap(self._scaled_pixmap())

    def heightForWidth(self, width: int) -> int:
        return (
            self.height()
            if self._pixmap is None or not self._pixmap.width()
            else int(self._pixmap.height() * width / self._pixmap.width())
        )

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self.width(), self.heightForWidth(self.width()))

    def _scaled_pixmap(self) -> QtGui.QPixmap:
        return self._pixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

    def resizeEvent(self, resize_event: QtGui.QResizeEvent):
        if self._pixmap is not None:
            super().setPixmap(self._scaled_pixmap())
