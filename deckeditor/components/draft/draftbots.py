import typing as t

import threading
import queue

from deckeditor.components.draft.bottemplate import DraftBot
from deckeditor.components.draft.randombot import RandomBot


class BotWorker(threading.Thread):

    def __init__(self):
        super().__init__()
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running:
            pass


def collect_bots() -> t.Mapping[str, t.Type[DraftBot]]:
    return {
        draft_bot_type.name: draft_bot_type
        for draft_bot_type in
        (RandomBot,)
    }
