import typing as t

from PyQt5.QtGui import QTransform


def serialize_transform(transform: QTransform) -> t.Sequence[int]:
    return (
        transform.m11(),
        transform.m12(),
        transform.m13(),
        transform.m21(),
        transform.m22(),
        transform.m23(),
        transform.m31(),
        transform.m32(),
        transform.m33(),
    )


def deserialize_transform(values: t.Sequence[int]) -> QTransform:
    return QTransform(*values)
