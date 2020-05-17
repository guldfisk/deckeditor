from PyQt5 import QtWidgets

from deckeditor.utils.version import version_formatted


class AboutDialog(QtWidgets.QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle('About')

        layout = QtWidgets.QFormLayout(self)

        layout.addRow('Version', QtWidgets.QLabel(version_formatted()))
        layout.addRow('Contact', QtWidgets.QLabel('ce.guldfisk@gmail.com'))
