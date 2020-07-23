import typing as t

from PyQt5.QtCore import pyqtSignal


class BoosterSpecificationSelectorInterface(object):
    booster_specification_value_changed: pyqtSignal

    def update_content(self, specification: t.Mapping[str, t.Any], enabled: bool) -> None:
        raise NotImplemented()
