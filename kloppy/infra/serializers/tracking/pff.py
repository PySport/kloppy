import logging
from datetime import timedelta, timezone
from dateutil.parser import parse
from typing import NamedTuple, IO, Optional, Union, Dict
import numpy as np
import json
import bz2
import io
import csv
from ast import literal_eval

from kloppy.domain import (
    DatasetFlag,
    Frame,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    PlayerData,
    Point,
    Point3D,
    PositionType,
    Provider,
    Team,
    TrackingDataset,
)

from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)

from kloppy.utils import performance_logging
from kloppy.io import FileLike

logger = logging.getLogger(__name__)

frame_rate = 10

position_types_mapping: Dict[str, PositionType] = {
    "CB": PositionType.CenterBack,  # Provider: CB
    "LCB": PositionType.LeftCenterBack,  # Provider: LCB
    "RCB": PositionType.RightCenterBack,  # Provider: RCB
    "LB": PositionType.LeftBack,  # Provider: LB
    "RB": PositionType.RightBack,  # Provider: RB
    "DM": PositionType.DefensiveMidfield,  # Provider: DM
    "CM": PositionType.CenterMidfield,  # Provider: CM
    "LW": PositionType.LeftWing,  # Provider: LW
    "RW": PositionType.RightWing,  # Provider: RW
    "D": PositionType.CenterBack,  # Provider: D (mapped to CenterBack)
    "CF": PositionType.Striker,  # Provider: CF
    "M": PositionType.CenterMidfield,  # Provider: M (mapped to CenterMidfield),
    "GK": PositionType.Goalkeeper,  # Provider: GK
    "F": PositionType.Striker,  # Provider: CF
}


class PFF_TrackingInputs(NamedTuple):
    meta_data: IO[bytes]
    roster_meta_data: IO[bytes]
    raw_data: FileLike


class PFF_TrackingDeserializer(
    TrackingDataDeserializer[PFF_TrackingInputs]
):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        include_empty_frames: Optional[bool] = False,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.include_empty_frames = include_empty_frames

    @property
    def provider(self) -> Provider:
        return Provider.PFF

    @classmethod
    def _get_frame_data(
        cls,
        game_id,
        teams,
        players,
        periods,
        frame,
    ):
        # Get Frame information
        frame_period = frame["period"]
        frame_id = str(game_id) + " - " + str(frame["frameNum"])
        frame_time = frame["periodGameClockTime"]

        # Ball coordinates
        if frame.get("ballsSmoothed") is not None:
            ball_x = frame.get("ballsSmoothed", {}).get("x")
            ball_y = frame.get("ballsSmoothed", {}).get("y")
            ball_z = frame.get("ballsSmoothed", {}).get("z")

            ball_coordinates = Point3D(
                x=float(ball_x) if ball_x is not None else None,
                y=float(ball_y) if ball_y is not None else None,
                z=float(ball_z) if ball_z is not None else None,
            )

        else:
            ball_coordinates = Point3D(x=None, y=None, z=None)

        # Player coordinates
        players_data = {}

        if frame["homePlayersSmoothed"] is not None:
            for home_player in frame["homePlayersSmoothed"]:
                for p_id, player in players["HOME"].items():
                    if player.jersey_no == str(home_player["jerseyNum"]):
                        # player_id = p_id
                        break

                home_player_x = home_player.get("x") if home_player else None
                home_player_y = home_player.get("y") if home_player else None

                player_data = PlayerData(
                    coordinates=Point(home_player_x, home_player_y)
                )
                players_data[player] = player_data

        if frame["awayPlayersSmoothed"] is not None:
            for away_player in frame["awayPlayersSmoothed"]:
                for p_id, player in players["AWAY"].items():
                    if player.jersey_no == str(away_player["jerseyNum"]):
                        # player_id = p_id
                        break

                away_player_x = away_player.get("x") if home_player else None
                away_player_y = away_player.get("y") if away_player else None

                player_data = PlayerData(
                    coordinates=Point(away_player_x, away_player_y)
                )
                players_data[player] = player_data

        ball_owning_team = None

        if frame.get("game_event") is not None:
            for team in teams:
                if frame["game_event"]["team_id"] is not None:
                    if team.team_id == frame["game_event"]["team_id"]:
                        ball_owning_team = team

        return Frame(
            frame_id=frame_id,
            timestamp=frame_time,
            ball_coordinates=ball_coordinates,
            players_data=players_data,
            period=periods[frame_period],
            ball_state=None,
            ball_owning_team=ball_owning_team,
            other_data={},
        )

    @classmethod
    def __get_periods(cls, tracking):
        """Gets the Periods contained in the tracking data"""
        periods = {}

        _periods = np.array([f["period"] for f in tracking])
        unique_periods = set(_periods)
        unique_periods = [
            period for period in unique_periods if period is not None
        ]

        for period in unique_periods:
            _frames = [
                frame for frame in tracking if frame["period"] == period
            ]

            periods[period] = Period(
                id=period,
                start_timestamp=timedelta(
                    seconds=_frames[0]["frameNum"] / frame_rate
                ),
                end_timestamp=timedelta(
                    seconds=_frames[-1]["frameNum"] / frame_rate
                ),
            )
        return periods

    def __load_json_raw(self, file_path):
        data = list()
        with bz2.open(file_path, "rt") as file:
            for line in file:
                data.append(json.loads(line))

        return data

        # with bz2.open(file_path, 'rt') as file:
        #     for line in file:
        #         yield json.loads(line)

    def __read_csv(self, file):

        # Read the content of the BufferedReader
        file_bytes = file.read()

        # Decode bytes to a string
        file_str = file_bytes.decode("utf-8")

        # Use StringIO to turn the string into a file-like object
        file_like = io.StringIO(file_str)

        return list(csv.DictReader(file_like))

    def deserialize(self, inputs: PFF_TrackingInputs) -> TrackingDataset:

        metadata = self.__read_csv(inputs.meta_data)
        roster_meta_data = self.__read_csv(inputs.roster_meta_data)
        raw_data = self.__load_json_raw(inputs.raw_data)

        # Obtain game_id from raw data
        game_id = int(raw_data[0]["gameRefId"])

        metadata = [row for row in metadata if int(row["id"]) == game_id]
        roster_meta_data = [
            row for row in roster_meta_data if int(row["game_id"]) == game_id
        ]

        home_team_id = literal_eval(metadata[0]["homeTeam"])["id"]
        away_team_id = literal_eval(metadata[0]["awayTeam"])["id"]

        with performance_logging("Loading metadata", logger=logger):
            periods = self.__get_periods(raw_data)

            pitch_size_width = literal_eval(metadata[0]["stadium"])[
                "pitchWidth"
            ]
            pitch_size_length = literal_eval(metadata[0]["stadium"])[
                "pitchLength"
            ]

            transformer = self.get_transformer(
                pitch_length=pitch_size_length, pitch_width=pitch_size_width
            )

            date = metadata[0]["date"]

            if date:
                date = parse(date).astimezone(timezone.utc)

            players = {"HOME": {}, "AWAY": {}}

            home_team = Team(
                team_id=home_team_id,
                name=literal_eval(metadata[0]["homeTeam"])["name"],
                ground=Ground.HOME,
            )
            away_team = Team(
                team_id=away_team_id,
                name=literal_eval(metadata[0]["awayTeam"])["name"],
                ground=Ground.AWAY,
            )
            teams = [home_team, away_team]

            for player in roster_meta_data:
                team_id = literal_eval(player["team"])["id"]
                player_col = literal_eval(player["player"])
                player_id = player_col["id"]
                player_name = player_col["nickname"]
                shirt_number = player["shirtNumber"]
                player_position = player["positionGroupType"]

                if team_id == home_team_id:
                    team_string = "HOME"
                    team = home_team
                elif team_id == away_team_id:
                    team_string = "AWAY"
                    team = away_team

                players[team_string][player_id] = Player(
                    player_id=f"{player_id}",
                    team=team,
                    jersey_no=f"{shirt_number}",
                    name=f"{player_name}",
                    starting_position=position_types_mapping.get(
                        player_position
                    ),
                )

            home_team.players = list(players["HOME"].values())
            away_team.players = list(players["AWAY"].values())

        with performance_logging("Loading data", logger=logger):

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for frame in raw_data:
                    frame_period = frame["period"]

                    if frame_period is not None:
                        if n % sample == 0:
                            yield frame
                        n += 1

        frames = []

        n_frames = 0
        for _frame in _iter():
            # include frame if there is any tracking data, players or ball.
            # or if include_empty_frames == True
            # if self.include_empty_frames:
            frame = self._get_frame_data(
                game_id,
                teams,
                players,
                periods,
                _frame,
            )

            # frame = transformer.transform_frame(frame)

            frames.append(frame)
            n_frames += 1

            if self.limit and n_frames >= self.limit:
                break

        orientation = Orientation.NOT_SET

        metadata = Metadata(
            teams=teams,
            periods=sorted(periods.values(), key=lambda p: p.id),
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=10,
            orientation=orientation,
            provider=Provider.PFF,
            flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
            coordinate_system=transformer.get_to_coordinate_system(),
            date=date,
            game_id=game_id,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
