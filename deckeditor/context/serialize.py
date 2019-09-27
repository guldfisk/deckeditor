import typing as t

from mtgorp.models.serilization.serializeable import SerializationException, Serializeable, M
from mtgorp.models.serilization.strategies.strategy import Strategy


class SoftSerialization(object):

    def __init__(
        self,
        strategy_priority: t.Iterable[Strategy],
        file_associations: t.Dict[str, Strategy],
    ):
        self._strategy_priority = list(strategy_priority)
        self._file_associations = {
            key.lower(): value
            for key, value in
            file_associations.items()
        } #type: t.Dict[str, Strategy]

    def serialize(self, serializeable: Serializeable, file_extension: str) -> str:
        file_extension = file_extension.lower()
        if file_extension in self._file_associations:
            return self._file_associations[file_extension].serialize(serializeable)

        for strategy in self._strategy_priority:
            try:
                return strategy.serialize(serializeable)

            except SerializationException:
                pass

        raise SerializationException('No matching strategy')

    def deserialize(self, cls: t.Type[M], s: str, file_extension: str) -> M:
        file_extension = file_extension.lower()
        if file_extension in self._file_associations:
            return self._file_associations[file_extension].deserialize(cls, s)

        for strategy in self._strategy_priority:
            try:
                return strategy.deserialize(cls, s)

            except SerializationException:
                pass

        raise SerializationException('No matching strategy')