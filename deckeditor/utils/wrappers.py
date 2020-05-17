import typing as t

from PyQt5 import QtCore

from deckeditor.context.context import Context


def notify_on_exception(
    exceptions: t.Sequence[t.Type[Exception]],
    formatter: t.Callable[[Exception], str] = lambda e: str(e),
):
    def wrapper(f: t.Callable) -> t.Callable:
        def wrapped(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions as e:
                Context.notification_message.emit(formatter(e))

        return wrapped

    return wrapper


def returns_q_variant(f: t.Callable[..., t.Any]) -> t.Callable[..., QtCore.QVariant]:
    def wrapped(*args, **kwargs) -> QtCore.QVariant:
        return QtCore.QVariant(f(*args, **kwargs))

    return wrapped
