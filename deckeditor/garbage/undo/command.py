import typing as t

from abc import ABC, abstractmethod


class UndoCommand(ABC):

    def setup(self):
        pass

    @abstractmethod
    def redo(self) -> None:
        pass

    def do(self):
        self.setup()
        self.redo()

    @abstractmethod
    def undo(self) -> None:
        pass

    def expecting(self) -> t.Tuple[t.Type['UndoCommand'], ...]:
        return ()

    def merge(self, command: 'UndoCommand') -> bool:
        return False

    def ignore(self) -> bool:
        return False

    def __repr__(self) -> str:
        return self.__class__.__name__


class CommandPackage(UndoCommand):

    def __init__(self, commands: t.Iterable[UndoCommand]):
        self._commands = list(commands)

    def add_command(self, command: UndoCommand):
        self._commands.append(command)

    def redo(self) -> None:
        for command in self._commands:
            command.redo()

    def undo(self) -> None:
        for command in reversed(self._commands):
            command.undo()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._commands})'

    def __getitem__(self, item) -> UndoCommand:
        return self._commands.__getitem__(item)


class UndoStack(object):

    def __init__(self, max_length: int = 32):
        self._commands = [] #type: t.List[UndoCommand]

        self._max_length = max_length #type: int

        self._head = -1 #type: int

        self._waiting_for = () #type: t.Tuple[t.Type[UndoCommand], ...]

    def _push(self, command: UndoCommand) -> None:

        if command.ignore():
            return

        if self._waiting_for:

            if any(
                isinstance(command, command_type)
                for command_type in
                self._waiting_for
            ):
                self._commands[-1].add_command(command)

            else:
                return

        else:

            self._commands = self._commands[:self._head + 1]

            if (
                self._commands
                and command.merge(
                self._commands[-1][-1]
                if isinstance(self._commands[-1], CommandPackage) else
                self._commands[-1]
            )
            ):
                if isinstance(self._commands[-1], CommandPackage):
                    self._commands[-1].add_command(command)

                else:
                    self._commands.append(
                        CommandPackage(
                            (
                                self._commands.pop(),
                                command,
                            )
                        )
                    )

            elif command.expecting():
                self._commands.append(
                    CommandPackage(
                        (command,)
                    )
                )

            else:
                self._commands.append(command)

        self._waiting_for = command.expecting()

        if 0 < self._max_length < len(self._commands):
            self._commands = self._commands[-self._max_length:]

        self._head = len(self._commands) - 1

        command.do()

    def push(self, *commands: UndoCommand) -> None:
        for command in commands:
            self._push(command)

    def can_undo(self) -> bool:
        return self._head >= 0 and not self._waiting_for

    def undo(self) -> None:
        if not self.can_undo():
            return

        self._commands[self._head].undo()

        self._head -= 1

    def can_redo(self) -> bool:
        return self._head < len(self._commands) - 1

    def redo(self) -> None:
        if not self.can_redo():
            return

        self._head += 1

        self._commands[self._head].redo()
