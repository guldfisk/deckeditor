from PyQt5 import QtCore, QtWidgets


class Spoiler(QtWidgets.QWidget):

    def __init__(self, title: str):
        super().__init__()
        
        self._title = title
        self._toggle_button = QtWidgets.QToolButton()
        self._toggle_button.setStyleSheet("QToolButton { border: none }")
        self._toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._toggle_button.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self._toggle_button.setText(title)
        self._toggle_button.setCheckable(True)
        self._toggle_button.setChecked(False)
        
        self._header_line = QtWidgets.QFrame()
        self._header_line.setFrameShape(QtWidgets.QFrame.HLine)
        self._header_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self._header_line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

        self._content_area = QtWidgets.QScrollArea()
        self._content_area.setStyleSheet("QScrollArea { background-color: white border: none }")
        self._content_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self._content_area.setMaximumHeight(0)
        self._content_area.setMinimumHeight(0)

        self._main_layout = QtWidgets.QGridLayout()
        self._main_layout.setVerticalSpacing(0)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.addWidget(self._toggle_button, 0, 0, 1, 1, QtCore.Qt.AlignLeft)
        self._main_layout.addWidget(self._header_line, 1, 2, 1, 1)
        self._main_layout.addWidget(self._content_area, 1, 0, 1, 3)

        self.setLayout(self._main_layout)

        self._toggle_button.clicked.connect(self._handle_toggle)
        
    def _handle_toggle(self, checked: bool) -> None:
        self._toggle_button.setArrowType(QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow)
    
    def set_content_layout(self, layout: QtWidgets.QLayout):
        self._content_area.setLayout(layout)
        collapsed_height = self.sizeHint().height() - self._content_area.maximumHeight()
        content_height = layout.sizeHint().height()
        self.setMinimumHeight(collapsed_height + content_height)
        self.setMaximumHeight(collapsed_height + content_height)
        self._content_area.setMaximumHeight(content_height)


# void Spoiler.setContentLayout(QLayout & contentLayout) {
#     delete contentArea.layout()
#     contentArea.setLayout(&contentLayout)
#     const auto collapsedHeight = sizeHint().height() - contentArea.maximumHeight()
#     auto contentHeight = contentLayout.sizeHint().height()
#     for (int i = 0 i < toggleAnimation.animationCount() - 1 ++i) {
#         QPropertyAnimation * spoilerAnimation = static_cast<QPropertyAnimation *>(toggleAnimation.animationAt(i))
#         spoilerAnimation->setDuration(animationDuration)
#         spoilerAnimation->setStartValue(collapsedHeight)
#         spoilerAnimation->setEndValue(collapsedHeight + contentHeight)
#     }
#     QPropertyAnimation * contentAnimation = static_cast<QPropertyAnimation *>(toggleAnimation.animationAt(toggleAnimation.animationCount() - 1))
#     contentAnimation->setDuration(animationDuration)
#     contentAnimation->setStartValue(0)
#     contentAnimation->setEndValue(contentHeight)
# }