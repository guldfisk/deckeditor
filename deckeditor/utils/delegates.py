# https://stackoverflow.com/questions/3363190/qt-qtableview-how-to-have-a-checkbox-only-column

import typing as t

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QEvent, QPoint, QRect
from PyQt5.QtWidgets import QStyledItemDelegate, QStyleOptionButton, QStyle, QApplication, QStyleOptionViewItem, QWidget


class CheckBoxDelegate(QStyledItemDelegate):

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> t.Optional[QWidget]:
        return None

    def paint(self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        checked = bool(index.model().data(index, Qt.DisplayRole))
        check_box_style_option = QStyleOptionButton()

        if (index.flags() & Qt.ItemIsEditable) != 0:
            check_box_style_option.state |= QStyle.State_Enabled
        else:
            check_box_style_option.state |= QStyle.State_ReadOnly

        if checked:
            check_box_style_option.state |= QStyle.State_On
        else:
            check_box_style_option.state |= QStyle.State_Off

        check_box_style_option.rect = self.get_checkbox_rect(option)

        # if not index.model().hasFlag(index, Qt.ItemIsEditable):
        # check_box_style_option.state |= QStyle.State_ReadOnly

        QApplication.style().drawControl(QStyle.CE_CheckBox, check_box_style_option, painter)

    def editorEvent(
        self,
        event: QtCore.QEvent,
        model: QtCore.QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> bool:
        '''
        Change the data in the model and the state of the checkbox
        if the user presses the left mousebutton or presses
        Key_Space or Key_Select and this cell is editable. Otherwise do nothing.
        '''
        if not (index.flags() & Qt.ItemIsEditable) != 0:
            return False

        # Do not change the checkbox-state
        if event.type() == QEvent.MouseButtonRelease or event.type() == QEvent.MouseButtonDblClick:
            if event.button() != Qt.LeftButton or not self.get_checkbox_rect(option).contains(event.pos()):
                return False
            if event.type() == QEvent.MouseButtonDblClick:
                return True
        elif event.type() == QEvent.KeyPress:
            if event.key() != Qt.Key_Space and event.key() != Qt.Key_Select:
                return False
        else:
            return False

        # Change the checkbox-state
        self.setModelData(None, model, index)
        return True

    def setModelData(self, editor: QWidget, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex) -> None:
        new_value = not bool(index.model().data(index, Qt.DisplayRole))
        model.setData(index, new_value, Qt.EditRole)

    def get_checkbox_rect(self, option: QStyleOptionViewItem) -> QRect:
        check_box_style_option = QStyleOptionButton()
        check_box_rect = QApplication.style().subElementRect(QStyle.SE_CheckBoxIndicator, check_box_style_option, None)
        check_box_point = QPoint(
            option.rect.x() +
            option.rect.width() / 2 -
            check_box_rect.width() / 2,
            option.rect.y() +
            option.rect.height() / 2 -
            check_box_rect.height() / 2
        )
        return QRect(check_box_point, check_box_rect.size())
