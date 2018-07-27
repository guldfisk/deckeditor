
from abc import ABC, abstractmethod

from mtgimg.interface import ImageRequest


class Signal(ABC):

	@abstractmethod
	def emit(self, image_request: ImageRequest):
		pass


class CardView(object):
	set_image = None #type: Signal