import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui

from mtgimg.interface import ImageRequest

from deckeditor.context.context import Context
from deckeditor.cardview.cardview import CardView


class ScaledLabel(QtWidgets.QLabel):

	def __init__(self, *args):
		super().__init__(*args)
		self.setMinimumSize(1, 1)
		self.setScaledContents(False)
		self._pixmap = None #type: t.Optional[QtGui.QPixmap]

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


class CardViewWidget(QtWidgets.QWidget, CardView):
	
	_image_ready = QtCore.pyqtSignal(ImageRequest, QtGui.QPixmap)
	set_image = QtCore.pyqtSignal(ImageRequest)

	def __init__(self, parent: t.Optional[QtWidgets.QWidget] = None):
		super().__init__(parent)

		self._image_request = None #type: ImageRequest
		self._pixmap = Context.pixmap_loader.get_default_pixmap()
		#type: QtGui.QPixmap

		self._info_label = ScaledLabel(self)
		self._info_label.setPixmap(self._pixmap)

		self._image_ready.connect(self._set_pixmap)
		self.set_image.connect(self._set_image)

		self._layout = QtWidgets.QVBoxLayout()

		self._layout.addWidget(self._info_label)

		self.setLayout(self._layout)

	def _set_pixmap(self, image_request: ImageRequest, pixmap: QtGui.QPixmap):
		if image_request == self._image_request:
			self._info_label.setPixmap(pixmap)
		
	def _set_image(self, image_request: ImageRequest) -> None:
		if image_request == self._image_request:
			return

		self._image_request = image_request
		Context.pixmap_loader.get_pixmap(
			image_request = image_request
		).then(
			lambda pixmap:
				self._image_ready.emit(
					image_request, pixmap
				)
		)

	def fit_image(self) -> None:
		self.resize(self._info_label.pixmap.size())

	def contextMenuEvent(self, context_event: QtGui.QContextMenuEvent):
		menu = QtWidgets.QMenu(self)

		resize = QtWidgets.QAction('100%', self)

		resize.triggered.connect(self.fit_image)

		menu.addAction(resize)

		menu.exec_(self.mapToGlobal(context_event.pos()))


