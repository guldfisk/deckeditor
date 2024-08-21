import typing as t

from PyQt5 import QtCore, QtGui, QtWidgets


class WithActions(object):
    def _create_action(self, name: str, result: t.Callable, shortcut: t.Optional[str] = None) -> QtWidgets.QAction:
        action = QtWidgets.QAction(name, self)
        action.triggered.connect(result)

        if shortcut:
            action.setShortcut(shortcut)
            action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self.addAction(action)

        return action

    def _create_shortcut(self, result: t.Callable, shortcut: t.Optional[str] = None) -> QtWidgets.QShortcut:
        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut), self)
        shortcut.activated.connect(result)
        shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        return shortcut
