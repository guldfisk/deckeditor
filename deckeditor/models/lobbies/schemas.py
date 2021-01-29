from hardcandy import fields
from hardcandy.schema import Schema


class LobbiesSchema(Schema):
    name = fields.Text()
    game_type = fields.Text()
    state = fields.Text()
    owner = fields.Text()
    users = fields.Lambda(
        lambda l: '{}/{}'.format(
            len(l.users),
            l.lobby_options.size,
        )
    )
    min_size = fields.Lambda(lambda l: l.lobby_options.minimum_size)
    requires_ready = fields.Lambda(lambda l: bool(l.lobby_options.require_ready), display_name = 'Req. Ready')
    auto_unready = fields.Lambda(lambda l: bool(l.lobby_options.unready_on_change))
