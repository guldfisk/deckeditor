import os
import typing as t
import uuid

from deckeditor.components.views.editables.editable import Editable


class EditablesMeta(object):

    def __init__(self, name: str, path: t.Optional[str] = None, key: t.Optional[str] = None):
        self._path: t.Optional[str] = path
        self._key = key if key is not None else str(uuid.uuid4())
        self._name: str = name

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        self._name = os.path.splitext(os.path.split(value)[1])[0]
        self._path = value

    @property
    def key(self) -> str:
        return self._key

    @property
    def name(self) -> str:
        return self._name

    @property
    def truncated_name(self) -> str:
        return self._name if len(self._name) <= 25 else self._name[:22] + '...'


class Editor(object):

    def current_editable(self) -> t.Optional[Editable]:
        pass

    def add_editable(self, editable: Editable, meta: EditablesMeta) -> Editable:
        pass

    def close_editable(self, editable: Editable) -> None:
        pass
