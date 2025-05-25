import json

from typing import Any, Dict, List, NamedTuple, IO, Optional, Tuple, Union

from kloppy.domain import (
    Provider,
    EventDataset,
    Metadata,
    Team,
    Player,
    DatasetFlag,
    Period,
)
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.exceptions import DeserializationError


class PFFEventDataInput(NamedTuple):
    """
    Input data for PFF event deserialization.
    """

    event_data: IO[bytes]
    meta_data: IO[bytes]
    roster_data: IO[bytes]


class PFFEventDeserializer(EventDataDeserializer[PFFEventDataInput]):
    """
    Deserialize PFF events.
    """

    def __init__(self, coordinate_system: Optional[Union[str, Provider]] = None):
        super().__init__(
            coordinate_system=coordinate_system,
        )

    @property
    def provider(self) -> Provider:
        return Provider.PFF

    def load_data(
        self, inputs: PFFEventDataInput
    ) -> tuple[IO[bytes], IO[bytes], IO[bytes]]:
        """
        Load data from the input files.
        """
        return (
            json.load(inputs.event_data),
            json.load(inputs.meta_data),
            json.load(inputs.roster_data),
        )

    def get_match_information(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get metadata from the input files.
        """
        return {
            "home_team": metadata["homeTeam"],
            "away_team": metadata["awayTeam"],
            "stadium": metadata["stadium"],
            "game_week": metadata["week"],
            "game_id": metadata["id"],
            "game_date": metadata["date"],
        }

    def get_pitch_information(
        self, stadium_metadata: Dict[str, Any]
    ) -> Tuple[float, float]:
        """
        Get pitch information from the metadata.
        """

        pitches: Dict[str, Any] = stadium_metadata["pitches"].pop()
        pitch_size_length = pitches["length"]
        pitch_size_width = pitches["width"]

        return pitch_size_width, pitch_size_length

    def build_player(self, player: Dict[str, Any], team: Team) -> Player:
        player = Player(
            player_id=player["player"]["id"],
            team=team,
            name=player["player"]["nickname"],
            jersey_no=int(player["shirtNumber"]),
            starting=player["started"],
            starting_position=player["positionGroupType"],
        )

        return player

    def build_squad(self, rooster_data: Dict[str, Any], team: Team) -> List[Player]:
        team_id = team.team_id

        players: List[Player] = [
            self.build_player(player_data, team_id)
            for player_data in rooster_data
            if player_data["team"]["id"] == team_id
        ]
        return players

    def build_team(
        self, team_data: Dict[str, Any], rooster_data: Dict[str, Any], ground_type: str
    ) -> Team:
        team_id = team_data["id"]

        team = Team(
            team_id=team_id,
            name=team_data["name"],
            ground=ground_type,
        )

        team.players = self.build_squad(rooster_data, team)

        return team

    def get_orientation(self, metadata: Dict[str, Any]) -> str:
        """
        Get the orientation of the event data.
        """

        is_home_team_left = metadata["homeTeamStartLeft"]

        orientation = "home-away" if is_home_team_left else "away-home"

        return orientation

    def get_metadata_information(
        self,
        match_information: Dict[str, Any],
        teams: List[Team],
        orientation: str,
        periods: str,
    ) -> Metadata:
        additional_metadata = {}

        metadata = Metadata(
            game_id=match_information["game_id"],
            game_week=match_information["game_week"],
            date=match_information["game_date"],
            teams=teams,
            pitch_dimensions=self.transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=None,
            orientation=orientation,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            score=None,
            provider=self.provider,
            coordinate_system=self.transformer.get_to_coordinate_system(),
            periods=periods,
            **additional_metadata,
        )

        return metadata

    def get_period_data(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the period data from the metadata.
        """

        period_data = {
            "first_period": {
                "id": 1,
                "start_timestamp": metadata["startPeriod1"],
                "end_timestamp": metadata["endPeriod1"],
            },
            "second_period": {
                "id": 2,
                "start_timestamp": metadata["startPeriod2"],
                "end_timestamp": metadata["endPeriod2"],
            },
        }

        return period_data

    def build_periods(self, metadata: Dict[str, Any]) -> List[Period]:
        """
        Get the periods of the event data.
        """

        period_data = self.get_period_data(metadata)

        periods = [Period(**data) for _, data in period_data.items()]

        return periods

    def deserialize(self, inputs: PFFEventDataInput) -> EventDataset:
        """
        Deserialize the PFF event.
        """
        try:
            raw_events, meta_data, roster_data = self.load_data(inputs)

            actual_meta_data = meta_data.pop()

            metadata_information = self.get_match_information(actual_meta_data)

            pitch_size_width, pitch_size_length = self.get_pitch_information(
                metadata_information["stadium"]
            )

            self.transformer = self.get_transformer(
                pitch_length=pitch_size_length,
                pitch_width=pitch_size_width,
                provider=self.provider,
            )

            teams = [
                self.build_team(
                    team_data=metadata_information["home_team"],
                    rooster_data=roster_data,
                    ground_type="home" if team == "home_team" else "away",
                )
                for team in ["home_team", "away_team"]
            ]

            orientation = self.get_orientation(actual_meta_data)

            periods = self.build_periods(
                metadata=actual_meta_data,
            )

            metadata = self.get_metadata_information(
                match_information=metadata_information,
                teams=teams,
                orientation=orientation,
                periods=periods,
            )

            return EventDataset(events=None, metadata=metadata)

        except Exception as e:
            raise DeserializationError(
                "Failed to create transformer for PFF event data"
            ) from e
