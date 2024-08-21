from PyQt5 import QtCore, QtWidgets


class DynamicSizeStack(QtWidgets.QStackedWidget):
    def sizeHint(self) -> QtCore.QSize:
        return self.currentWidget().sizeHint()

    def minimumSizeHint(self) -> QtCore.QSize:
        return self.currentWidget().minimumSizeHint()
