from __future__ import annotations

from enum import Enum

from magiccube.laps.tickets.ticket import BaseTicket
from magiccube.laps.traps.trap import BaseTrap
from mtgorp.models.interfaces import Card, Cardboard, Printing
from mtgorp.models.persistent.attributes.colors import Color
from mtgorp.models.persistent.attributes.typeline import LAND
from PyQt5 import QtGui

from deckeditor.components.cardview.focuscard import Focusable


class UIColor(Enum):
    WHITE = QtGui.QColor(156, 145, 51)
    BLUE = QtGui.QColor(78, 97, 241)
    BLACK = QtGui.QColor(36, 35, 36)
    RED = QtGui.QColor(134, 75, 71)
    GREEN = QtGui.QColor(108, 166, 112)
    MUD = QtGui.QColor(58, 54, 53)
    LAND = QtGui.QColor(95, 64, 44)
    GOLD = QtGui.QColor(192, 163, 66)
    TRAP = QtGui.QColor(67, 58, 77)
    TICKET = QtGui.QColor(102, 152, 138)
    PURPLE = QtGui.QColor(86, 39, 94)

    @classmethod
    def for_card(cls, card: Card) -> UIColor:
        if len(card.color) == 1:
            return UI_COLOR_MAP[card.color.__iter__().__next__()]

        if not card.color:
            if LAND in card.type_line:
                return cls.LAND
            return cls.MUD

        return cls.GOLD

    @classmethod
    def for_focusable(cls, focusable: Focusable) -> UIColor:
        if isinstance(focusable, Printing):
            return UIColor.for_card(focusable.cardboard.front_card)

        if isinstance(focusable, Cardboard):
            return UIColor.for_card(focusable.front_card)

        if isinstance(focusable, BaseTrap):
            return UIColor.TRAP

        if isinstance(focusable, BaseTicket):
            return UIColor.TICKET

        return UIColor.PURPLE


UI_COLOR_MAP = {
    Color.WHITE: UIColor.WHITE,
    Color.BLUE: UIColor.BLUE,
    Color.BLACK: UIColor.BLACK,
    Color.RED: UIColor.RED,
    Color.GREEN: UIColor.GREEN,
}
