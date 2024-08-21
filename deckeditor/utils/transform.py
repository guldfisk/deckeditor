import typing as t

from PyQt5.QtGui import QTransform


def transform_factory(
    horizontal_scaling_factor: float = 1.0,
    vertical_shearing_factor: float = 0.0,
    horizontal_projection_factor: float = 0.0,
    horizontal_shearing_factor: float = 0.0,
    vertical_scaling_factor: float = 1.0,
    vertical_projection_factor: float = 0.0,
    horizontal_translation_factor: float = 0.0,
    vertical_translation_factor: float = 0.0,
    division_factor: float = 1.0,
) -> QTransform:
    return QTransform(
        horizontal_scaling_factor,
        vertical_shearing_factor,
        horizontal_projection_factor,
        horizontal_shearing_factor,
        vertical_scaling_factor,
        vertical_projection_factor,
        horizontal_translation_factor,
        vertical_translation_factor,
        division_factor,
    )


def serialize_transform(matrix: QTransform) -> t.Sequence[int]:
    return (
        matrix.m11(),
        matrix.m12(),
        matrix.m13(),
        matrix.m21(),
        matrix.m22(),
        matrix.m23(),
        matrix.m31(),
        matrix.m32(),
        matrix.m33(),
    )


def deserialize_transform(values: t.Sequence[int]) -> QTransform:
    return QTransform(*values)
