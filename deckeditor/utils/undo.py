import typing as t

from PyQt5.QtWidgets import QUndoCommand


class CommandPackage(QUndoCommand):
    def __init__(self, modifications: t.Sequence[QUndoCommand]):
        self._modifications = modifications
        super().__init__("intra modification")

    def redo(self) -> None:
        for modification in self._modifications:
            modification.redo()

    def undo(self) -> None:
        for modification in reversed(self._modifications):
            modification.undo()
