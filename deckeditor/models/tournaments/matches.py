import typing as t

from cubeclient.models import ScheduledMatch, ScheduledSeat
from hardcandy import fields
from hardcandy.schema import Schema

from deckeditor import values
from deckeditor.context.context import Context


class MatchSchema(Schema):
    tournament = fields.Lambda(lambda m: m.tournament.name)
    round = fields.Lambda(lambda m: m.round + 1)
    opponents = fields.Lambda(
        lambda m: ", ".join(sorted(seat.participant.tag_line for seat in MatchSchema.get_opponents(m)))
    )
    tournament_participants = fields.Lambda(lambda m: ", ".join(sorted(p.tag_line for p in m.tournament.participants)))
    created_at = fields.Lambda(lambda m: m.tournament.created_at.strftime(values.STANDARD_DATETIME_FORMAT))

    @classmethod
    def get_opponents(cls, match: ScheduledMatch) -> t.Iterator[ScheduledSeat]:
        current_user = Context.cube_api_client.user
        for seat in match.seats:
            if seat.participant.player is None or seat.participant.player.id != current_user.id:
                yield seat
