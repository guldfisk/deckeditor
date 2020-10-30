from __future__ import annotations

from abc import ABC

from PyQt5 import QtWidgets, QtCore, QtGui

from yeetlong.multiset import Multiset

from mtgorp.models.persistent.expansion import Expansion

from deckeditor.context.context import Context


class Signal(ABC):

    def emit(self, pool_key: Multiset[Expansion]):
        pass


class PoolGenerateable(object):

    pool_generated = None #type: Signal


class ExpansionSelector(QtWidgets.QComboBox):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        for target in Context.db.expansions.keys():
            self.addItem(target)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            self.nextInFocusChain().setFocus()

        else:
            super().keyPressEvent(key_event)


class Amounter(QtWidgets.QLineEdit):

    def __init__(self, locked: bool = False, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._locked = locked

        self.setValidator(QtGui.QIntValidator(1, 99, self))
        self.setText('6')

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            self.parent().parent().add_selector_box()

        else:
            super().keyPressEvent(key_event)

        if not self.text():
            if self._locked:
                self.setText('1')

            else:
                self.parent().setParent(None)

    def focusInEvent(self, focus_event: QtGui.QFocusEvent):
        super().focusInEvent(focus_event)
        self.selectAll()


class ExpansionSelectorBox(QtWidgets.QGroupBox):

    def __init__(self, locked: bool, parent: GeneratePoolDialog):
        super().__init__(parent)
        self._expansion_selector = ExpansionSelector()
        self._amounter = Amounter(locked, parent)

        self._layout = QtWidgets.QHBoxLayout()

        self._layout.addWidget(self._expansion_selector)
        self._layout.addWidget(self._amounter)

        self.setLayout(self._layout)

    def parent(self) -> GeneratePoolDialog:
        return super().parent()

    @property
    def expansion_selector(self) -> ExpansionSelector:
        return self._expansion_selector

    @property
    def amounter(self) -> Amounter:
        return self._amounter


class GeneratePoolDialog(QtWidgets.QDialog):

    def __init__(self, generateable: PoolGenerateable, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self._generateable = generateable

        self._ok_button = QtWidgets.QPushButton('Ok', self)

        self._top_box = QtWidgets.QHBoxLayout()
        self._bottom_box = QtWidgets.QHBoxLayout()

        self._bottom_box.addWidget(self._ok_button)

        self._layout = QtWidgets.QVBoxLayout()

        self._layout.addLayout(self._top_box)
        self._layout.addLayout(self._bottom_box)

        self.setLayout(self._layout)

        self.add_selector_box(locked = True)

        self._ok_button.clicked.connect(self._generate)

    def add_selector_box(self, locked = False):
        box = ExpansionSelectorBox(locked, self)
        self._top_box.addWidget(box, alignment = QtCore.Qt.AlignLeft)
        self.setTabOrder(box.expansion_selector, box.amounter)
        self.setTabOrder(box.amounter, self._ok_button)
        box.expansion_selector.setFocus()

    def _generate(self) -> None:
        self.accept()

        expansions = Multiset()

        for child in self.children():
            if isinstance(child, ExpansionSelectorBox):
                expansions.add(
                    Context.db.expansions[
                        child.expansion_selector.currentText()
                    ],
                    int(child.amounter.text()),
                )

        self._generateable.pool_generated.emit(expansions)
