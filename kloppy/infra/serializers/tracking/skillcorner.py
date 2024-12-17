import json
import logging
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import IO, Dict, NamedTuple, Optional, Union

from kloppy.domain import (
    AttackingDirection,
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
    Score,
    Team,
    TrackingDataset,
    attacking_direction_from_frame,
)
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)

frame_rate = 10

position_types_mapping: Dict[int, PositionType] = {
    1: PositionType.Unknown,
    2: PositionType.CenterBack,  # Provider: CB
    3: PositionType.LeftCenterBack,  # Provider: LCB
    4: PositionType.RightCenterBack,  # Provider: RCB
    5: PositionType.LeftBack,  # Provider: LWB (mapped to Left Back)
    6: PositionType.RightBack,  # Provider: RWB (mapped to Right Back)
    7: PositionType.DefensiveMidfield,  # Provider: DM
    8: PositionType.CenterMidfield,  # Provider: CM
    9: PositionType.LeftMidfield,  # Provider: LM
    10: PositionType.RightMidfield,  # Provider: RM
    11: PositionType.AttackingMidfield,  # Provider: AM
    12: PositionType.LeftWing,  # Provider: LW
    13: PositionType.RightWing,  # Provider: RW
    14: PositionType.LeftForward,  # Provider: LF
    15: PositionType.Striker,  # Provider: CF (mapped to Striker)
    16: PositionType.RightForward,  # Provider: RF
    17: PositionType.Unknown,  # Provider: SUB (mapped to Unknown)
}


class SkillCornerInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class SkillCornerDeserializer(TrackingDataDeserializer[SkillCornerInputs]):
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
        return Provider.SKILLCORNER

    @classmethod
    def _get_frame_data(
        cls,
        teams,
        teamdict,
        players,
        player_id_to_team_dict,
        periods,
        player_dict,
        anon_players,
        ball_id,
        referee_dict,
        frame,
    ):
        frame_period = frame["period"]

        frame_id = frame["frame"]
        frame_time = cls._timestamp_from_timestring(frame["time"])

        if frame_period == 1:
            frame_time -= timedelta(seconds=0)
        elif frame_period == 2:
            frame_time -= timedelta(seconds=45 * 60)
        # TODO: check if the below is correct; just guessing here
        elif frame_period == 3:
            frame_time -= timedelta(seconds=90 * 60)
        elif frame_period == 4:
            frame_time -= timedelta(seconds=105 * 60)
        elif frame_period == 5:
            frame_time -= timedelta(seconds=120 * 60)
        else:
            raise ValueError(f"Unknown period id {frame_period}")

        ball_coordinates = None
        players_data = {}

        # ball_carrier = frame["possession"].get("trackable_object")
        ball_owning_team = frame["possession"].get("group")

        if ball_owning_team == "home team":
            ball_owning_team = teams[0]
        elif ball_owning_team == "away team":
            ball_owning_team = teams[1]
        else:
            ball_owning_team = None

        for frame_record in frame["data"]:
            # containing x, y, trackable_object, track_id, group_name
            x = frame_record.get("x")
            y = frame_record.get("y")

            trackable_object = frame_record.get("trackable_object", None)

            track_id = frame_record.get("track_id", None)
            group_name = frame_record.get("group_name", None)

            if trackable_object == ball_id or group_name == "balls":
                group_name = "balls"
                z = frame_record.get("z")
                if z is not None:
                    z = float(z)
                ball_coordinates = Point3D(x=float(x), y=float(y), z=z)
                continue

            elif (
                trackable_object in referee_dict.keys()
                or group_name == "referee"
            ):
                group_name = "referee"
                continue  # Skip Referee Coords

            if group_name is None:
                group_name = teamdict.get(
                    player_id_to_team_dict.get(trackable_object)
                )

                if group_name == "home_team":
                    player = players["HOME"][trackable_object]
                elif group_name == "away_team":
                    player = players["AWAY"][trackable_object]

            if trackable_object is None:
                player_id = str(track_id)
                if group_name == "home team":
                    if f"anon_{player_id}" not in anon_players["HOME"].keys():
                        player = cls.__create_anon_player(teams, frame_record)
                        anon_players["HOME"][f"anon_home_{player_id}"] = player
                    else:
                        player = anon_players["HOME"][f"anon_home_{player_id}"]

                elif group_name == "away team":
                    if f"anon_{player_id}" not in anon_players["AWAY"].keys():
                        player = cls.__create_anon_player(teams, frame_record)
                        anon_players["AWAY"][f"anon_away_{player_id}"] = player
                    else:
                        player = anon_players["AWAY"][f"anon_away_{player_id}"]

            players_data[player] = PlayerData(coordinates=Point(x, y))

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
    def _timestamp_from_timestring(cls, timestring):
        parts = timestring.split(":")

        if len(parts) == 2:
            m, s = parts
            return timedelta(seconds=60 * float(m) + float(s))
        elif len(parts) == 3:
            h, m, s = parts
            return timedelta(
                seconds=3600 * float(h) + 60 * float(m) + float(s)
            )
        else:
            raise ValueError("Invalid timestring format")

    @classmethod
    def _get_skillcorner_attacking_directions(cls, frames, periods):
        """
        with only partial tracking data we cannot rely on a single frame to
        infer the attacking directions as a simple average of only some players
        x-coords might not reflect the attacking direction.
        """
        attacking_directions = {}

        # Group attacking directions by period ID
        period_direction_map = defaultdict(list)
        for frame in frames:
            if len(frame.players_data) > 0:
                direction = attacking_direction_from_frame(frame)
            else:
                direction = AttackingDirection.NOT_SET
            period_direction_map[frame.period.id].append(direction)

        # Determine the most common attacking direction for each period
        for period_id in periods.keys():
            if period_id in period_direction_map:
                count = Counter(period_direction_map[period_id])
                attacking_directions[period_id] = count.most_common(1)[0][0]
            else:
                attacking_directions[period_id] = AttackingDirection.NOT_SET

        return attacking_directions

    @staticmethod
    def __replace_timestamp(obj):
        if "timestamp" in obj:
            obj["time"] = obj.pop("timestamp")
        return obj

    def __load_json_raw(self, file):
        if Path(file.name).suffix == ".jsonl":
            data = []
            for line in file:
                obj = json.loads(line)
                data.append(self.__replace_timestamp(obj))
            return data
        else:
            data = json.load(file)
            for line in data:
                line = self.__replace_timestamp(line)
            return data

    @classmethod
    def __get_periods(cls, tracking):
        """gets the Periods contained in the tracking data"""
        periods = {}

        # Extract unique periods while filtering out None values
        unique_periods = {
            frame["period"]
            for frame in tracking
            if frame["period"] is not None
        }

        for period in unique_periods:
            # Filter frames that belong to the current period and have valid "time"
            _frames = [
                frame
                for frame in tracking
                if frame["period"] == period and frame["time"] is not None
            ]

            # Ensure _frames is not empty before accessing the first and last elements
            if _frames:
                periods[period] = Period(
                    id=period,
                    start_timestamp=timedelta(
                        seconds=_frames[0]["frame"] / frame_rate
                    ),
                    end_timestamp=timedelta(
                        seconds=_frames[-1]["frame"] / frame_rate
                    ),
                )

        return periods

    @classmethod
    def __create_anon_player(cls, teams, frame_record):
        """
        creates a Player object for a track_id'ed player with known team membership but unknown identity.

        Args:
            frame_record (dict): dictionary containing 'x', 'y', 'track_id' and 'group_name'

        Returns:
            kloppy.domain.models.common.Player

        """
        track_id = frame_record.get("track_id", None)
        group_name = frame_record.get("group_name", None)

        if group_name == "home team":
            team = teams[0]
        elif group_name == "away team":
            team = teams[1]
        else:
            raise ValueError(
                f"anonymous player with track_id `{track_id}` does not have a specified group_name."
            )

        return Player(
            player_id=f"{team.ground}_anon_{track_id}",
            team=team,
            jersey_no=None,
            name=f"Anon_{track_id}",
            first_name="Anon",
            last_name=track_id,
            starting=None,
            starting_position=None,
            attributes={},
        )

    def deserialize(self, inputs: SkillCornerInputs) -> TrackingDataset:
        metadata = json.load(inputs.meta_data)
        raw_data = self.__load_json_raw(inputs.raw_data)

        with performance_logging("Loading metadata", logger=logger):
            periods = self.__get_periods(raw_data)

            teamdict = {
                metadata["home_team"].get("id"): "home_team",
                metadata["away_team"].get("id"): "away_team",
            }

            player_to_team_dict = {
                player["trackable_object"]: player["team_id"]
                for player in metadata["players"]
            }

            player_dict = {
                player["trackable_object"]: player
                for player in metadata["players"]
            }

            referee_dict = {
                ref["trackable_object"]: "referee"
                for ref in metadata["referees"]
            }
            ball_id = metadata["ball"]["trackable_object"]

            # there are different pitch_sizes in SkillCorner
            pitch_size_width = metadata["pitch_width"]
            pitch_size_length = metadata["pitch_length"]

            transformer = self.get_transformer(
                pitch_length=pitch_size_length, pitch_width=pitch_size_width
            )

            home_team_id = metadata["home_team"]["id"]
            away_team_id = metadata["away_team"]["id"]

            players = {"HOME": {}, "AWAY": {}}

            home_team = Team(
                team_id=home_team_id,
                name=metadata["home_team"]["name"],
                ground=Ground.HOME,
            )
            away_team = Team(
                team_id=away_team_id,
                name=metadata["away_team"]["name"],
                ground=Ground.AWAY,
            )
            teams = [home_team, away_team]

            date = metadata.get("date_time")
            if date:
                date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )

            game_id = metadata.get("id")
            if game_id:
                game_id = str(game_id)

            home_team_coach = metadata.get("home_team_coach")
            if home_team_coach is not None:
                home_coach = f"{home_team_coach['first_name']} {home_team_coach['last_name']}"

            away_team_coach = metadata.get("away_team_coach")
            if away_team_coach is not None:
                away_coach = f"{away_team_coach['first_name']} {away_team_coach['last_name']}"

            if game_id:
                game_id = str(game_id)

            for player_track_obj_id, player in player_dict.items():
                team_id = player["team_id"]

                if team_id == home_team_id:
                    team_string = "HOME"
                    team = home_team
                elif team_id == away_team_id:
                    team_string = "AWAY"
                    team = away_team

                players[team_string][player_track_obj_id] = Player(
                    player_id=f"{player['id']}",
                    team=team,
                    jersey_no=player["number"],
                    name=f"{player['first_name']} {player['last_name']}",
                    first_name=player["first_name"],
                    last_name=player["last_name"],
                    starting=player["start_time"] == "00:00:00",
                    starting_position=position_types_mapping.get(
                        player["player_role"]["id"], PositionType.Unknown
                    ),
                    attributes={},
                )

            home_team.players = list(players["HOME"].values())
            away_team.players = list(players["AWAY"].values())

        anon_players = {"HOME": {}, "AWAY": {}}

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
            if self.include_empty_frames or len(_frame["data"]) > 0:
                frame = self._get_frame_data(
                    teams,
                    teamdict,
                    players,
                    player_to_team_dict,
                    periods,
                    player_dict,
                    anon_players,
                    ball_id,
                    referee_dict,
                    _frame,
                )

                frame = transformer.transform_frame(frame)

                frames.append(frame)
                n_frames += 1

                if self.limit and n_frames >= self.limit:
                    break

        attacking_directions = self._get_skillcorner_attacking_directions(
            frames, periods
        )
        if attacking_directions[1] == AttackingDirection.LTR:
            orientation = Orientation.HOME_AWAY
        elif attacking_directions[1] == AttackingDirection.RTL:
            orientation = Orientation.AWAY_HOME
        else:
            warnings.warn(
                "Could not determine orientation of dataset, defaulting to NOT_SET"
            )
            orientation = Orientation.NOT_SET

        metadata = Metadata(
            teams=teams,
            periods=sorted(periods.values(), key=lambda p: p.id),
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=Score(
                home=metadata["home_team_score"],
                away=metadata["away_team_score"],
            ),
            frame_rate=10,
            orientation=orientation,
            provider=Provider.SKILLCORNER,
            flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
            coordinate_system=transformer.get_to_coordinate_system(),
            date=date,
            game_id=game_id,
            home_coach=home_coach,
            away_coach=away_coach,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
