from hardcandy import fields
from hardcandy.schema import Schema

from deckeditor import values


class MatchSchema(Schema):
    tournament = fields.Lambda(lambda m: m.tournament.name)
    round = fields.Lambda(lambda m: m.round + 1)
    match_participants = fields.Lambda(
        lambda m: ', '.join(
            sorted(
                seat.participant.tag_line
                for seat in
                m.seats
            )
        )
    )
    tournament_participants = fields.Lambda(
        lambda m: ', '.join(
            sorted(
                p.tag_line
                for p in
                m.tournament.participants
            )
        )
    )
    created_at = fields.Lambda(
        lambda m: m.tournament.created_at.strftime(values.STANDARD_DATETIME_FORMAT)
    )
