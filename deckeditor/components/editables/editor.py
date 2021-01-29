import typing as t
import os
import uuid
from abc import abstractmethod

from deckeditor.components.views.editables.editable import Editable, Tab


class TabMeta(object):

    def __init__(self, name: str, path: t.Optional[str] = None, key: t.Optional[str] = None):
        self._path: t.Optional[str] = path
        self._key = key if key is not None else str(uuid.uuid4())
        self._name: str = name

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        self._name = os.path.split(value)[-1]
        self._path = value

    @property
    def key(self) -> str:
        return self._key

    @property
    def name(self) -> str:
        return self._name

    @property
    def truncated_name(self) -> str:
        return self._name if len(self._name) <= 25 else self._name[:11] + '...' + self._name[-11:]

    def __hash__(self) -> int:
        return hash(self._key)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, self.__class__)
            and self._key == other._key
        )

    def __repr__(self) -> str:
        return '{}({}, {})'.format(
            self.__class__.__name__,
            self._name,
            self._key,
        )


class Editor(object):

    @abstractmethod
    def current_editable(self) -> t.Optional[Editable]:
        pass

    @abstractmethod
    def add_editable(self, editable: Editable, meta: TabMeta) -> Editable:
        pass

    @abstractmethod
    def close_tab(self, tab: Tab) -> None:
        pass

    @abstractmethod
    def open_limited_deck(self, deck_id: t.Union[str, int]) -> None:
        pass
