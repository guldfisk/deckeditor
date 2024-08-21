import time
import typing as t

from magiccube.collections.cube import Cube
from magiccube.collections.cubeable import Cubeable
from mtgdraft.models import DraftBooster

from deckeditor.components.draft.bots.randombot import RandomBot
from deckeditor.components.draft.bots.redbot import RedBot
from deckeditor.components.draft.bottemplate import DraftBot
from deckeditor.context.context import Context


def bot_pick(
    bot: DraftBot,
    booster: DraftBooster,
    pool: Cube,
    delay: int,
    callback: t.Callable[[Cubeable, DraftBooster], None],
):
    st = time.time()
    pick = bot.make_pick(Context.db, booster, pool)
    if delay:
        time.sleep(delay - (time.time() - st))
    callback(pick, booster)


def collect_bots() -> t.Mapping[str, t.Type[DraftBot]]:
    return {draft_bot_type.name: draft_bot_type for draft_bot_type in (RandomBot, RedBot)}
