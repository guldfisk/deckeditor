from abc import abstractmethod, ABC

from magiccube.collections.cubeable import Cubeable
from mtgdraft.models import Booster
from mtgorp.db.database import CardDatabase


class DraftBot(ABC):
    name: str

    @classmethod
    @abstractmethod
    def make_pick(cls, db: CardDatabase, booster: Booster) -> Cubeable:
        pass
