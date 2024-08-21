from magiccube.collections.cubeable import Cubeable
from mtgorp.models.interfaces import Cardboard, Printing
from PyQt5.QtCore import QModelIndex, Qt

from deckeditor.models.sequence import GenericItemSequence


class CardboardList(GenericItemSequence[Cardboard]):
    def data(self, index: QModelIndex, role: int = ...) -> str:
        if role == Qt.DisplayRole:
            cardboard = self.get_item(index)
            if cardboard:
                return cardboard.name


class PrintingList(GenericItemSequence[Printing]):
    def data(self, index: QModelIndex, role: int = ...) -> str:
        if role == Qt.DisplayRole:
            printing = self.get_item(index)
            if printing:
                return printing.cardboard.name


class CubeablesList(GenericItemSequence[Cubeable]):
    def data(self, index: QModelIndex, role: int = ...) -> str:
        if role == Qt.DisplayRole:
            cubeable = self.get_item(index)
            if cubeable:
                return cubeable.cardboard.name if isinstance(cubeable, Printing) else cubeable.description


class ExpansionPrintingList(PrintingList):
    def data(self, index: QModelIndex, role: int = ...) -> str:
        if role == Qt.DisplayRole:
            printing = self.get_item(index)
            if printing:
                return f"{printing.expansion.name} - {printing.expansion.code}"
