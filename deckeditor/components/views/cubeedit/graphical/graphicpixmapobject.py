import math
import typing as t

from PyQt5 import QtCore, QtGui, QtWidgets

from deckeditor.utils.colors import overlay_colors


class GraphicPixmapObject(QtWidgets.QGraphicsObject):
    INFO_TEXT_X_OFFSET, INFO_TEXT_Y_OFFSET = 30, 100

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

        self._highlight: t.Optional[QtGui.QColor] = None
        self._info_text: t.Optional[str] = None

    def set_info_text(self, text: str) -> None:
        self._info_text = text
        self.update()

    def add_highlight(self, color: QtGui.QColor) -> None:
        self._highlight = color if self._highlight is None else overlay_colors(color, self._highlight)
        self.update()

    def clear_highlight(self) -> None:
        self._highlight = None
        self.update()

    def pixmap(self):
        return self._pixmap

    def set_pixmap(self, pixmap: QtGui.QPixmap):
        self._pixmap = pixmap
        self._bounding_rect = QtCore.QRectF(0, 0, pixmap.size().width(), pixmap.size().height())

    def boundingRect(self) -> QtCore.QRectF:
        return self._bounding_rect

    def paint(self, painter: QtGui.QPainter, options, widget=None):
        painter.drawPixmap(self._zero_point, self._pixmap)

        if self._highlight is not None:
            painter.setBrush(QtGui.QBrush(self._highlight))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(self._bounding_rect)
            painter.setBrush(QtGui.QBrush())

        if self._info_text is not None:
            painter.setFont(QtGui.QFont("Helvetica", 32))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(230, 230, 230, 180)))
            painter.setPen(QtCore.Qt.NoPen)

            text_rect = painter.fontMetrics().boundingRect(self._info_text)
            top_corner = self._bounding_rect.adjusted(self.INFO_TEXT_X_OFFSET, self.INFO_TEXT_Y_OFFSET, 0, 0).topLeft()
            painter.drawRect(
                text_rect.adjusted(
                    self.INFO_TEXT_X_OFFSET, self.INFO_TEXT_Y_OFFSET, self.INFO_TEXT_X_OFFSET, self.INFO_TEXT_Y_OFFSET
                )
            )

            painter.setPen(QtGui.QPen(QtGui.QColor(10, 10, 10, 230)))
            painter.drawText(top_corner, self._info_text)

        if self.isSelected():
            pen_width = math.ceil(self._selection_highlight_pen.width() / 2) - 1

            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(self._selection_highlight_pen)
            painter.drawRect(
                self.boundingRect().adjusted(
                    pen_width,
                    pen_width,
                    -pen_width,
                    -pen_width,
                )
            )
