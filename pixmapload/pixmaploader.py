
from promise import Promise
from PyQt5 import QtGui

from mtgorp.models.persistent import printing as _printing
from mtgimg import load as imageload

class PixmapLoader(imageload.Loader):
	@classmethod
	def get_pixmap(
		cls,
		printing: _printing.Printing = None,
		back: bool = False,
		crop: bool = False,
		image_request: imageload.ImageRequest = None
	) -> Promise:
		return cls.get_image(
			printing,
			back,
			crop,
			image_request,
		).then(
			lambda image: QtGui.QPixmap.fromImage(
				QtGui.ImageQt.ImageQt(
					image
				)
			)
		)
	@classmethod
	def get_default_pixmap(cls):
		print('get default pixmap')
		return cls.get_default_image().then(
			lambda image: QtGui.QPixmap.fromImage(QtGui.ImageQt.ImageQt(image))
		)