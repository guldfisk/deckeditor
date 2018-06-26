
from abc import abstractmethod


class Notifyable(object):

	@abstractmethod
	def notify(self, message: str) -> None:
		pass