import math
import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore


class GraphicPixmapObject(QtWidgets.QGraphicsObject):

    def __init__(self, pixmap: t.Optional[QtGui.QPixmap] = None):
        super().__init__()
        self._pixmap: t.Optional[QtGui.QPixmap] = None
        self._bounding_rect = QtCore.QRectF()

        self._selection_highlight_pen = QtGui.QPen(
            QtGui.QColor(255, 0, 0),
            10,
        )

        self._zero_point = QtCore.QPointF(0, 0)

        if pixmap is not None:
            self.set_pixmap(pixmap)

    def pixmap(self):
        return self._pixmap

    def set_pixmap(self, pixmap: QtGui.QPixmap):
        self._pixmap = pixmap
        self._bounding_rect = QtCore.QRectF(
            0,
            0,
            pixmap.size().width(),
            pixmap.size().height()
        )

    def boundingRect(self):
        return self._bounding_rect

    def paint(self, painter: QtGui.QPainter, options, widget=None):
        painter.drawPixmap(self._zero_point, self._pixmap)

        if self.isSelected():
            pen_width = math.ceil(self._selection_highlight_pen.width() / 2) - 1

            painter.setPen(self._selection_highlight_pen)
            painter.drawRect(
                self.boundingRect().adjusted(
                    pen_width,
                    pen_width,
                    -pen_width,
                    -pen_width,
                )
            )
