import copy
import typing as t

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget

from mtgorp.models.tournaments.matches import MatchType
from mtgorp.models.tournaments.tournaments import Tournament

from deckeditor.components.lobbies.interfaces import LobbyViewInterface
from deckeditor.components.lobbies.options import primitives


class TournamentComboSelector(primitives.ComboSelector):

    def _on_activated(self, idx: int) -> None:
        tournament_options = copy.copy(self._lobby_view.lobby.game_options['tournament_options'])
        tournament_options[self._option] = self.itemText(idx)

        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {
                'tournament_options': tournament_options,
            },
        )


class TournamentIntegerConfigSelector(primitives.IntegerOptionSelector):

    def __init__(
        self,
        lobby_view: LobbyViewInterface,
        option: str,
        config_option: str,
        allowed_range: t.Tuple[int, int] = (1, 180),
    ):
        super().__init__(lobby_view, allowed_range)
        self._option = option
        self._config_option = config_option
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, value: int) -> None:
        tournament_options = copy.copy(self._lobby_view.lobby.game_options['tournament_options'])
        if not self._option in tournament_options:
            tournament_options[self._option] = {}
        tournament_options[self._option][self._config_option] = value

        self._lobby_view.lobby_model.set_options(
            self._lobby_view.lobby.name,
            {
                'tournament_options': tournament_options,
            },
        )


class TournamentOptionsSelector(QWidget):

    def __init__(self, lobby_view: LobbyViewInterface):
        super().__init__()

        self._lobby_view = lobby_view

        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tournament_type_selector = TournamentComboSelector(
            self._lobby_view,
            'tournament_type',
            Tournament.tournaments_map.keys(),
        )

        self._rounds_selector = TournamentIntegerConfigSelector(
            self._lobby_view,
            'tournament_config',
            'rounds',
            (1, 128),
        )

        self._match_type_selector = TournamentComboSelector(
            self._lobby_view,
            'match_type',
            MatchType.matches_map.keys(),
        )

        self._match_games_selector = TournamentIntegerConfigSelector(
            self._lobby_view,
            'match_config',
            'n',
            (1, 19),
        )

        layout.addRow('Tournament Type', self._tournament_type_selector)
        layout.addRow('Tournament Rounds', self._rounds_selector)
        layout.addRow('Match Type', self._match_type_selector)
        layout.addRow('Match Games', self._match_games_selector)

    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        selected_tournament_type = Tournament.tournaments_map[options['tournament_type']]
        selected_match_type = MatchType.matches_map[options['match_type']]
        self._tournament_type_selector.update_content(options['tournament_type'], enabled)
        self._rounds_selector.update_content(
            options['tournament_config'].get('rounds', 0),
            enabled and 'rounds' in selected_tournament_type.options_schema.fields,
        )
        self._match_type_selector.update_content(options['match_type'], enabled)
        self._match_games_selector.update_content(
            options['match_config'].get('n', 0),
            enabled and 'n' in selected_match_type.options_schema.fields,
        )
