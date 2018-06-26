import typing as t
from concurrent.futures import Executor, ThreadPoolExecutor
import os
from threading import Lock

from PIL import ImageQt, Image
from promise import Promise
from PyQt5.QtGui import QPixmap

from mtgimg.load import Loader as ImageLoader, TaskAwaiter
from mtgimg.interface import ImageRequest, picturable

from deckeditor import paths

IMAGE_PATH = os.path.join(paths.RESOURCE_PATH, '599.png')


class SingleAccessDict(dict):

	def __init__(self):
		super().__init__()
		self._lock = Lock()

	def __getitem__(self, k):
		with self._lock:
			return super().__getitem__(k)

	def __setitem__(self, k, v) -> None:
		with self._lock:
			super().__setitem__(k, v)


class _PixmapConverter(object):

	def __init__(self):
		self._pixmaps = SingleAccessDict()  # type: t.Dict[ImageRequest, QPixmap]
		self._processing = TaskAwaiter()

	def get_pixmap(self, image_request: t.Optional[ImageRequest], image: Image.Image):
		try:
			return self._pixmaps[image_request]
		except KeyError:
			pass

		condition, in_progress = self._processing.get_condition(image_request)

		if in_progress:
			with condition:
				condition.wait()

			return self._pixmaps[image_request]

		self._pixmaps[image_request] = pixmap = QPixmap.fromImage(
			ImageQt.ImageQt(
				image
			)
		)

		self._pixmaps[image_request] = pixmap

		with condition:
			condition.notify_all()

		return pixmap


class PixmapLoader(ImageLoader):

	def __init__(
		self,
		printing_executor: t.Union[Executor, int] = None,
		imageable_executor: t.Union[Executor, int] = None,
		pixmap_executor: t.Union[Executor, int] = None,
	):
		super().__init__(printing_executor, imageable_executor)
		# self._pixmaps = SingleAccessDict() #type: t.Dict[ImageRequest, QPixmap]

		self._pixmap_executor = (
			pixmap_executor
			if pixmap_executor is isinstance(pixmap_executor, Executor) else
			ThreadPoolExecutor(
				max_workers = pixmap_executor if isinstance(pixmap_executor, int) else 10
			)
		)

		self._pixmap_converter = _PixmapConverter()

	# def _image_to_pixmap(self, image_request: t.Optional[ImageRequest], image: Image.Image) -> QPixmap:
	# 	print('_image to pixmap')
	# 	try:
	# 		pixmap = self._pixmaps[image_request]
	# 		print('cached')
	# 		return pixmap
	# 	except KeyError:
	#
	# 		self._pixmaps[image_request] = pixmap = QPixmap.fromImage(
	# 			ImageQt.ImageQt(image)
	# 		)
	# 		print('converted, saved')
	# 		return pixmap

	def get_pixmap(
		self,
		pictured: picturable = None,
		back: bool = False,
		crop: bool = False,
		image_request: ImageRequest = None
	) -> Promise:

		_image_request = (
			ImageRequest(pictured, back, crop)
			if image_request is None else
			image_request
		)

		return self.get_image(
			image_request = _image_request,
		).then(
			lambda image:
				self._pixmap_executor.submit(
					self._pixmap_converter.get_pixmap,
					_image_request,
					image,
				)
			# lambda image: QPixmap.fromImage(ImageQt.ImageQt(image))
		)

	def get_default_pixmap(self) -> Promise:
		return self.get_default_image().then(
			lambda image: self._pixmap_converter.get_pixmap(None, image)
		)