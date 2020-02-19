import typing as t

from deckeditor.components.views.editables.editable import Editable


class Editor(object):

    def current_editable(self) -> t.Optional[Editable]:
        pass
