import random

from mtgorp.db.database import CardDatabase

from magiccube.collections.cube import Cube
from magiccube.collections.cubeable import Cubeable

from mtgdraft.models import Booster

from deckeditor.components.draft.bottemplate import DraftBot


class RandomBot(DraftBot):
    name = 'Random'

    @classmethod
    def make_pick(cls, db: CardDatabase, booster: Booster, pool: Cube) -> Cubeable:
        return random.choice(list(booster.cubeables))
