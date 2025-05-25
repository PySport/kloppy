import json

from typing import Any, Dict, List, NamedTuple, IO, Optional, Tuple, Union

from kloppy.domain import Provider, EventDataset, Metadata, Team, Player
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

    def get_match_information(self, metadata: List) -> Dict[str, Any]:
        """
        Get metadata from the input files.
        """
        return {
            "home_team": metadata["homeTeam"],
            "away_team": metadata["awayTeam"],
            "stadium": metadata["stadium"],
            "game_week": metadata["week"],
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

    def build_team(self, team_data: Dict[str, Any], rooster_data: Dict[str, Any], ground_type: str) -> Team:

        team_id = team_data["id"]

        team = Team(
            team_id=team_id,
            name=team_data["name"],
            ground=ground_type,
        )

        team.players = self.build_squad(rooster_data, team)

        return team

    # def get_metadata_information(self) -> Metadata:

    #     metadata = Metadata(
    #             teams=teams,
    #             periods=periods,
    #             pitch_dimensions=self.transformer.get_to_coordinate_system().pitch_dimensions,
    #             frame_rate=None,
    #             orientation=Orientation.ACTION_EXECUTING_TEAM,
    #             flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
    #             score=None,
    #             provider=Provider.STATSBOMB,
    #             coordinate_system=self.transformer.get_to_coordinate_system(),
    #             **additional_metadata,
    #         )

    #     return metadata

    @property
    def provider(self) -> Provider:
        return Provider.PFF

    def deserialize(self, inputs: PFFEventDataInput) -> EventDataset:
        """
        Deserialize the PFF event.
        """
        try:
            raw_events, meta_data, roster_data = self.load_data(inputs)

            metadata_information = self.get_match_information(meta_data.pop())

            pitch_size_width, pitch_size_length = self.get_pitch_information(
                metadata_information["stadium"]
            )

            self.transformer = self.get_transformer(
                pitch_length=pitch_size_length,
                pitch_width=pitch_size_width,
                provider=self.provider,
            )

            home_team = self.build_team(
                team_data=metadata_information["home_team"],
                rooster_data=roster_data,
                ground_type="home",
            )

        except Exception as e:
            raise DeserializationError(
                "Failed to create transformer for PFF event data"
            ) from e
