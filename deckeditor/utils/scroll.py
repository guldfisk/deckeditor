from PyQt5 import QtWidgets
from PyQt5.QtCore import QEvent, QObject, Qt


class VerticalScrollArea(QtWidgets.QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def eventFilter(self, o: QObject, e: QEvent) -> bool:
        if o == self.widget() and e.type() == QEvent.Resize:
            self.setMinimumWidth(self.widget().minimumSizeHint().width() + self.verticalScrollBar().width())
        return False
