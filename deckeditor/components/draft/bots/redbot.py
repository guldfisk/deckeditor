import random

from magiccube.collections.cube import Cube
from magiccube.collections.cubeable import Cubeable
from mtgdraft.models import DraftBooster
from mtgorp.db.database import CardDatabase
from mtgorp.models.persistent.attributes.colors import Color
from mtgorp.tools.search.pattern import PrintingPatternBuilder

from deckeditor.components.draft.bottemplate import DraftBot


class RedBot(DraftBot):
    name = "Red"

    pattern = PrintingPatternBuilder().color.equals(frozenset((Color.RED,))).all()

    @classmethod
    def make_pick(cls, db: CardDatabase, booster: DraftBooster, pool: Cube) -> Cubeable:
        red_printings = list(cls.pattern.matches(booster.cubeables.printings))
        if red_printings:
            return min(red_printings, key=lambda p: p.cardboard.front_card.cmc)
        if booster.cubeables.traps:
            return max(booster.cubeables.traps, key=lambda trap: len(list(cls.pattern.matches(trap.node))))
        return random.choice(list(booster.cubeables))
