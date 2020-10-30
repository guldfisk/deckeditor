from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog

from mtgorp.models.persistent.attributes.expansiontype import ExpansionType

from deckeditor.context.context import Context


class DBInfoDialog(QDialog):
    _date_format = '%Y/%m/%d %H:%M:%S'

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QFormLayout(self)

        layout.addRow('Type', QtWidgets.QLabel(Context.db.__class__.__name__))
        layout.addRow('Last updated', QtWidgets.QLabel(Context.db.created_at.strftime(self._date_format)))
        layout.addRow('JSON last updated', QtWidgets.QLabel(Context.db.json_version.strftime(self._date_format)))
        layout.addRow(
            'Latest set',
            QtWidgets.QLabel(
                sorted(
                    filter(lambda e: e.expansion_type == ExpansionType.SET, Context.db.expansions.values()),
                    key = lambda e: e.release_date
                )[-1].name,
            )
        )
        layout.addRow(
            'Latest expansion',
            QtWidgets.QLabel(
                sorted(
                    Context.db.expansions.values(),
                    key = lambda e: e.release_date
                )[-1].name,
            )
        )
        layout.addRow('Checksum', QtWidgets.QLabel(Context.db.checksum.hex()))
