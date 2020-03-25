import random

from deckeditor.components.draft.bottemplate import DraftBot
from magiccube.collections.cubeable import Cubeable
from mtgdraft.models import Booster
from mtgorp.db.database import CardDatabase


class RandomBot(DraftBot):
    name = 'Random'

    @classmethod
    def make_pick(cls, db: CardDatabase, booster: Booster) -> Cubeable:
        return random.choice(list(booster.cubeables))
