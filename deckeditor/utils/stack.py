from PyQt5 import QtWidgets, QtCore


class DynamicSizeStack(QtWidgets.QStackedWidget):

    def sizeHint(self) -> QtCore.QSize:
        return self.currentWidget().sizeHint()

    def minimumSizeHint(self) -> QtCore.QSize:
        return self.currentWidget().minimumSizeHint()
