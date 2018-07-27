
from PyQt5 import QtWidgets, QtGui, QtCore


class Cursor(QtWidgets.QGraphicsItem):

	def __init__(self, parent=None):
		super().__init__(parent)

		self._fill_color = QtGui.QColor(0, 0, 255, 100)

		self._brush = QtGui.QBrush(self._fill_color, QtCore.Qt.SolidPattern)

		self._pen = QtGui.QPen(
			QtGui.QColor(0, 0, 255),
			10,
		)

		self._middle_pen = QtGui.QPen(
			QtGui.QColor(20, 20, 40),
			10,
		)

		self._bounding_rect = QtCore.QRectF(-55, -55, 205, 205)

		self._collision_path = QtGui.QPainterPath()
		self._collision_path.addRect(QtCore.QRectF())

	def boundingRect(self) -> QtCore.QRectF:
		return self._bounding_rect

	def shape(self) -> QtGui.QPainterPath:
		return self._collision_path

	def paint(
		self,
		painter: QtGui.QPainter,
		style_options: QtWidgets.QStyleOptionGraphicsItem,
		widget: QtWidgets.QWidget = None,
	):
		painter.setPen(self._pen)
		painter.setBrush(self._brush)
		painter.drawEllipse(QtCore.QPointF(50, 50), 100, 100)
		painter.setPen(self._middle_pen)
		painter.drawEllipse(QtCore.QPointF(50, 50), 5, 5)