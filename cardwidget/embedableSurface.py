from PyQt5 import QtWidgets, QtGui

class EmbeddedSurface(QtWidgets.QWidget):
	def __init__(self, parent=None):
		super(EmbeddedSurface, self).__init__(parent)
		self.setMinimumSize(1, 1)
		self.data = None
		self.image = None
	def update_image(self, surface):
		self.data = surface.get_buffer().raw
		self.image = QtGui.QImage(self.data, surface.get_width(), surface.get_height(), QtGui.QImage.Format_RGB32)
	def get_surface(self):
		raise NotImplemented
	def resizeEvent(self, event):
		self.update_image(self.get_surface())
	def paintEvent(self, event):
		qp=QtGui.QPainter()
		qp.begin(self)
		qp.drawImage(0, 0, self.image)
		qp.end()
	def redraw(self):
		self.update_image(self.get_surface())
		self.update()