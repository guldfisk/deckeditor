

from PyQt5 import QtSvg, QtCore, QtGui


class Values(object):
	SVG_DATA = 1
	SVG_TEXT_FORMAT = QtGui.QTextFormat.UserObject + 1


class SvgTextObject(QtCore.QObject, QtGui.QTextObject):

	def intrinsicSize(self, document: QtGui.QTextDocument, i: int, text_format: QtGui.QTextFormat) -> QtCore.QSizeF:
		size = text_format.property(Values.SVG_DATA).size()

		if size.height() < 25:
			return size * 25 / size.height()

		return size

	def drawObject(
		self,
		painter: QtGui.QPainter,
		rectangle: QtCore.QRectF,
		document: QtGui.QTextDocument,
		i: int,
		text_format: QtGui.QTextFormat,
	):
		painter.drawImage(
			rectangle,
			text_format.property(Values.SVG_DATA),
		)