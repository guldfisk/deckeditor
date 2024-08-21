from abc import ABC, abstractmethod

from magiccube.collections.cube import Cube
from magiccube.collections.cubeable import Cubeable
from mtgdraft.models import DraftBooster
from mtgorp.db.database import CardDatabase


class DraftBot(ABC):
    name: str

    @classmethod
    @abstractmethod
    def make_pick(cls, db: CardDatabase, booster: DraftBooster, picks: Cube) -> Cubeable:
        pass
