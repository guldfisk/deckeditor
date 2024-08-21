import typing as t

from cubeclient.models import ScheduledMatch
from promise import Promise
from PyQt5.QtCore import QObject, pyqtSignal

from deckeditor.context.context import Context


class ScheduledMatchesController(QObject):
    matches_changed = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._matches = set()
        Context.token_changed.connect(lambda s: self.refresh())

    @property
    def matches(self) -> t.AbstractSet[ScheduledMatch]:
        return self._matches

    def _set_matches(self, matches: t.AbstractSet[ScheduledMatch]) -> t.AbstractSet[ScheduledMatch]:
        if matches == self._matches:
            return self._matches

        self._matches = matches
        self.matches_changed.emit(self._matches)

        return matches

    def refresh(self) -> Promise[t.AbstractSet[ScheduledMatch]]:
        if Context.cube_api_client is None or Context.cube_api_client.user is None:
            return Promise.resolve(set())

        return Context.cube_api_client.scheduled_matches(Context.cube_api_client.user.id).then(self._set_matches)


MATCHES_CONTROLLER = ScheduledMatchesController()
