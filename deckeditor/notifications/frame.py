import time
import typing as t
from threading import Lock, Thread

from PyQt5 import QtCore, QtWidgets

from deckeditor.notifications.notification import Notification


class Alarm(Thread):
    def __init__(self, callback: t.Callable, *args, delay: float = 4.0):
        super().__init__()
        self._callback = callback
        self._args = args
        self._delay = delay

    def run(self):
        time.sleep(self._delay)
        self._callback(*self._args)


class SingleAccessList(list):
    def __init__(self):
        super().__init__()
        self._lock = Lock()

    def __iter__(self) -> t.Iterator:
        with self._lock:
            for item in super().__iter__():
                yield item

    def remove(self, item: t.Any) -> None:
        with self._lock:
            super().remove(item)

    def append(self, item: t.Any) -> None:
        with self._lock:
            super().append(item)


class NotificationFrame(object):
    def __init__(self, window: QtWidgets.QMainWindow, spacing: int = 10):
        self._window = window
        self._spacing = spacing

        self._notifications: t.List[Notification] = SingleAccessList()

    def stack_notifications(self):
        position = self._window.height()

        for notification in self._notifications:
            position -= notification.height() + self._spacing

            notification.move(
                self._window.width() - notification.width() - self._spacing,
                position,
            )

    def notify(self, message: str) -> None:
        notification = Notification(
            self._window,
            message,
        )

        self._notifications.append(notification)

        notification.signal.connect(self._remove_notification)
        Alarm(
            self._remove_notification,
            notification,
            delay=QtCore.QSettings().value("notification_linger_duration", 4.5, float),
        ).start()

        notification.show()

        self.stack_notifications()

    def _remove_notification(self, notification):
        try:
            self._notifications.remove(notification)
        except ValueError:
            return

        notification.hide()
        self.stack_notifications()
