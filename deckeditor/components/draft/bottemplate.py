from abc import abstractmethod, ABC

from mtgorp.db.database import CardDatabase

from magiccube.collections.cube import Cube
from magiccube.collections.cubeable import Cubeable

from mtgdraft.models import DraftBooster


class DraftBot(ABC):
    name: str

    @classmethod
    @abstractmethod
    def make_pick(cls, db: CardDatabase, booster: DraftBooster, picks: Cube) -> Cubeable:
        pass
