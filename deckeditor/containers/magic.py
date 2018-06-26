import typing as t


from mtgorp.models.collections.serilization.serializeable import Serializeable, model_tree
from mtgorp.models.persistent.printing import Printing


class CardPackage(Serializeable):

	def __init__(self, printings: t.Iterable[Printing]) -> None:
		self._printings = tuple(printings)

	def to_model_tree(self) -> model_tree:
		return {
			'printings': self._printings,
		}

	@classmethod
	def from_model_tree(cls, tree: model_tree) -> 'Serializeable':
		return cls(model_tree['printings'])

	def __hash__(self) -> int:
		return hash(self._printings)

	def __eq__(self, other: object) -> bool:
		return (
			isinstance(other, self.__class__)
			and self._printings == other._printings
		)