from PyQt5 import QtWidgets, QtGui, QtCore

class GraphicPixmapObject(QtWidgets.QGraphicsObject):
	def __init__(self):
		super().__init__()
		self._pixmap = None  # type: QtGui.QPixmap
		self._bounding_rect = QtCore.QRectF()

	def pixmap(self):
		return self._pixmap

	def setPixmap(self, pixmap: 'QtGui.QPixmap'):
		self._pixmap = pixmap
		self._bounding_rect = QtCore.QRectF(0, 0, pixmap.size().width(), pixmap.size().height())

	def paint(self, painter: QtGui.QPainter, options, widget=None):
		painter.drawPixmap(QtCore.QPointF(0, 0), self._pixmap)
		if self.isSelected():
			painter.setPen(self._selection_highlite_pen)
			painter.drawRect(self.boundingRect())
