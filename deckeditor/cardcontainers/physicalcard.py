
from PyQt5 import QtCore, QtGui, QtWidgets

from mtgorp.models.persistent.printing import Printing
from mtgorp.db.static import MtgDb

from deckeditor.pixmapload.pixmaploader import PixmapLoader
from deckeditor.cardcontainers.graphicpixmapobject import GraphicPixmapObject


class PhysicalCard(GraphicPixmapObject):

	signal = QtCore.pyqtSignal(QtGui.QPixmap)
	pixmap_loader = PixmapLoader()

	DEFAULT_PIXMAP = None #type: QtGui.QPixmap

	@classmethod
	def init(cls):
		cls.DEFAULT_PIXMAP = cls.pixmap_loader.get_default_pixmap().get()

	def __init__(self, printing: Printing):
		super().__init__(self.DEFAULT_PIXMAP)

		self._selection_highlight_pen = QtGui.QPen(
			QtGui.QColor(255, 0, 0),
			QtCore.QSettings().value('card_selected_frame_width', 5),
		)

		self._printing = printing

		self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)

		self.signal.connect(self._set_pixmap)

		self._set_image(self._printing)

	# def mousePressEvent(self, QGraphicsSceneMouseEvent):
	# 	pass

	@property
	def printing(self):
		return self._printing

	def _set_image(self, printing: Printing):
		self.pixmap_loader.get_pixmap(printing).then(self.signal.emit)

	def _set_pixmap(self: 'PhysicalCard', pixmap: QtGui.QPixmap):
		print('set pixmap thingy', self)
		self.set_pixmap(pixmap)
		self.update()

	def mouseDoubleClickEvent(self, mouse_event):
		print('double clicked', self)
		# self._set_image(MtgDb.db.cardboards['Lightning Bolt'].from_expansion('LEA'))
