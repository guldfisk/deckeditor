import typing as t

from PyQt5.QtGui import QColor


def average_colors(colors: t.Sequence[QColor]) -> QColor:
    return QColor(
        *(
            sum(
                getattr(c, v)()
                for c in colors
            ) / len(colors)
            for v in
            ('red', 'green', 'blue', 'alpha')
        )
    )


def overlay_colors(bottom: QColor, top: QColor) -> QColor:
    bottom_multiplier = (1 - (top.alpha() / 255)) * (bottom.alpha() / 255)
    top_multiplier = top.alpha() / 255
    alpha_multiplier = bottom_multiplier + top_multiplier
    return QColor(
        (bottom.red() * bottom_multiplier + top.red() * top_multiplier) / alpha_multiplier,
        (bottom.green() * bottom_multiplier + top.green() * top_multiplier) / alpha_multiplier,
        (bottom.blue() * bottom_multiplier + top.blue() * top_multiplier) / alpha_multiplier,
        alpha_multiplier * 255,
    )


def color_values(color: QColor) -> t.Tuple[int, int, int, int]:
    return color.red(), color.green(), color.blue(), color.alpha()
