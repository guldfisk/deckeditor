import typing as t

from PyQt5 import QtCore, QtGui, QtWidgets

from yeetlong.multiset import Multiset

from mtgorp.models.persistent.printing import Printing
from mtgorp.tools.groupification import groupification


class DeckListContent(QtWidgets.QWidget):

    def __init__(self, scroll_area: QtWidgets.QScrollArea, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._scroll_area = scroll_area

        self._maindeck_label = QtWidgets.QLabel(self)
        self._sideboard_label = QtWidgets.QLabel(self)

        self._layout = QtWidgets.QHBoxLayout()

        self._layout.addWidget(self._maindeck_label, alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._layout.addWidget(self._sideboard_label, alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        self.setLayout(self._layout)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    @property
    def maindeck_label(self) -> QtWidgets.QLabel:
        return self._maindeck_label

    @property
    def sideboard_label(self) -> QtWidgets.QLabel:
        return self._sideboard_label

    def resizeEvent(self, resize_event: QtGui.QResizeEvent):
        super().resizeEvent(resize_event)

        self._scroll_area.setMinimumWidth(
            self.maindeck_label.minimumSizeHint().width()
            + self.sideboard_label.minimumSizeHint().width()
            + 40
        )


class DeckListWidget(QtWidgets.QWidget):
    set_deck = QtCore.pyqtSignal(object, object)

    _MAINDECK_PRINTING_GROUPIFYER = groupification.PrintingGroupifyer(
        'Maindeck',
        (
            groupification.CREATURE_CATEGORY,
            groupification.INSTANT_SORCERY_CATEGORY,
            groupification.NON_CREATURE_PERMANENTS_CATEGORY,
            groupification.LANDS_CATEGORY,
        ),
    )

    _SIDEBOARD_PRINTING_GROUPIFYER = groupification.PrintingGroupifyer(
        'Sideboard',
        (
            groupification.CREATURE_CATEGORY,
            groupification.INSTANT_SORCERY_CATEGORY,
            groupification.NON_CREATURE_PERMANENTS_CATEGORY,
            groupification.LANDS_CATEGORY,
        ),
    )

    _MAINDECK_CARDBOARD_GROUPIFYER = groupification.CardboardGroupifyer(
        'Maindeck',
        (
            groupification.CREATURE_CATEGORY,
            groupification.INSTANT_SORCERY_CATEGORY,
            groupification.NON_CREATURE_PERMANENTS_CATEGORY,
            groupification.LANDS_CATEGORY,
        ),
    )

    _SIDEBOARD_CARDBOARD_GROUPIFYER = groupification.CardboardGroupifyer(
        'Sideboard',
        (
            groupification.CREATURE_CATEGORY,
            groupification.INSTANT_SORCERY_CATEGORY,
            groupification.NON_CREATURE_PERMANENTS_CATEGORY,
            groupification.LANDS_CATEGORY,
        ),
    )

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._maindeck_printings = Multiset() #type: Multiset[Printing]
        self._sideboard_printings = Multiset() #type: Multiset[Printing]

        self._view_as_printings = False

        self._scroll_area = QtWidgets.QScrollArea()

        self._content_view = DeckListContent(self._scroll_area)

        self._scroll_area.setWidget(self._content_view)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self._scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)


        self._layout = QtWidgets.QVBoxLayout()

        self._layout.addWidget(self._scroll_area)

        self.setLayout(self._layout)

        self.set_deck.connect(self._set_deck)

        self._view_as_printings_action = QtWidgets.QAction('View as Printings', self)
        self._view_as_printings_action.triggered.connect(lambda : self._set_view_as_printings(True))
        self._view_as_printings_action.setShortcut('Ctrl+P')
        self._view_as_printings_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

        self._view_as_cardboard_action = QtWidgets.QAction('View as Cardboard', self)
        self._view_as_cardboard_action.triggered.connect(lambda : self._set_view_as_printings(False))
        self._view_as_cardboard_action.setShortcut('Ctrl+C')
        self._view_as_cardboard_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

    def _set_view_as_printings(self, value: bool) -> None:
        if value == self._view_as_printings:
            return

        self._view_as_printings = value

        self._reset_deck()

    @property
    def _maindeck_groupifyer(self):
        return (
            self._MAINDECK_PRINTING_GROUPIFYER
            if self._view_as_printings else
            self._MAINDECK_CARDBOARD_GROUPIFYER
        )

    @property
    def _sideboard_groupifyer(self):
        return (
            self._SIDEBOARD_PRINTING_GROUPIFYER
            if self._view_as_printings else
            self._SIDEBOARD_CARDBOARD_GROUPIFYER
        )

    def _reset_deck(self) -> None:
        if self._view_as_printings:
            maindeck = self._maindeck_printings
            sideboard = self._sideboard_printings
        else:
            maindeck = (printing.cardboard for printing in self._maindeck_printings)
            sideboard = (printing.cardboard for printing in self._sideboard_printings)

        self._content_view.maindeck_label.setText(
            str(
                self._maindeck_groupifyer.groupify(
                    maindeck
                )
            )
        )

        self._content_view.sideboard_label.setText(
            str(
                self._sideboard_groupifyer.groupify(
                    sideboard
                )
            )
        )

    def _set_deck(self, maindeck: t.Iterable[Printing], sideboard: t.Iterable[Printing]) -> None:
        self._maindeck_printings = Multiset(maindeck)
        self._sideboard_printings = Multiset(sideboard)

        self._reset_deck()

    def contextMenuEvent(self, context_event: QtGui.QContextMenuEvent) -> None:
        menu = QtWidgets.QMenu(self)

        menu.addActions(
            (
                self._view_as_cardboard_action,
                self._view_as_printings_action,
            )
        )

        menu.exec_(self.mapToGlobal(context_event.pos()))


