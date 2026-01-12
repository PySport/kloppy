from datetime import datetime, timedelta
import json
import logging
from typing import IO, NamedTuple, Optional, Union

from kloppy.domain import (
    BallState,
    DatasetFlag,
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
from kloppy.domain.services.frame_factory import create_frame
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)

# Mapping from CDF position codes to kloppy PositionType
position_types_mapping: dict[str, PositionType] = {
    "LW": PositionType.LeftWing,
    "LCF": PositionType.LeftForward,
    "CF": PositionType.Striker,
    "RCF": PositionType.RightForward,
    "RW": PositionType.RightWing,
    "LAM": PositionType.LeftAttackingMidfield,
    "CAM": PositionType.CenterAttackingMidfield,
    "RAM": PositionType.RightAttackingMidfield,
    "LM": PositionType.LeftMidfield,
    "LCM": PositionType.LeftCentralMidfield,
    "CM": PositionType.CentralMidfield,
    "RCM": PositionType.RightCentralMidfield,
    "RM": PositionType.RightMidfield,
    "LDM": PositionType.LeftDefensiveMidfield,
    "CDM": PositionType.CenterDefensiveMidfield,
    "RDM": PositionType.RightDefensiveMidfield,
    "LB": PositionType.LeftBack,
    "LCB": PositionType.LeftCenterBack,
    "CB": PositionType.CenterBack,
    "RCB": PositionType.RightCenterBack,
    "RB": PositionType.RightBack,
    "GK": PositionType.Goalkeeper,
    "SUB": PositionType.Unknown,
}

# Mapping from CDF period names to period IDs
PERIOD_NAME_TO_ID = {
    "first_half": 1,
    "second_half": 2,
    "first_half_extratime": 3,
    "second_half_extratime": 4,
    "shootout": 5,
}


class CDFTrackingDataInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class CDFTrackingDeserializer(TrackingDataDeserializer[CDFTrackingDataInputs]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        include_empty_frames: Optional[bool] = False,
        only_alive: bool = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.include_empty_frames = include_empty_frames
        self.only_alive = only_alive

    @property
    def provider(self) -> Provider:
        return Provider.CDF

    @staticmethod
    def _validate_cdf_data(metadata_content: dict, first_frame: dict):
        """Validate CDF data using common-data-format-validator.

        Uses soft validation which emits warnings for schema violations
        rather than raising exceptions.
        """
        try:
            import cdf

            # Validate metadata with soft=True (emits warnings)
            meta_validator = cdf.MetaSchemaValidator(
                schema=f"cdf/files/v{cdf.VERSION}/schema/meta.json"
            )
            meta_validator.validate_schema(metadata_content, soft=True)

            # Validate first tracking frame with soft=True (emits warnings)
            tracking_validator = cdf.TrackingSchemaValidator(
                schema=f"cdf/files/v{cdf.VERSION}/schema/tracking.json"
            )
            tracking_validator.validate_schema(first_frame, soft=True)

        except ImportError:
            raise ImportError(
                "common-data-format-validator package is required for CDF validation. "
                "Please install the latest version: pip install common-data-format-validator"
            )

    @staticmethod
    def _validate_orientation(
        frames: list, teams: list[Team], periods: list[Period]
    ):
        """Validate that data conforms to CDF STATIC_HOME_AWAY orientation.

        CDF standard: Home team always plays left to right, meaning the home
        goalkeeper should always be on the left side (negative x) in every period.
        Uses average GK position over first 5 frames per period.
        Raises ValueError if data doesn't conform.
        """
        home_team = teams[0]  # Ground.HOME

        for period in periods:
            # Get first 5 frames for this period
            period_frames = [f for f in frames if f.period.id == period.id][:5]
            if not period_frames:
                continue

            # Collect GK x-coordinates across frames
            gk_x_positions = []
            for frame in period_frames:
                for player, player_data in frame.players_data.items():
                    if (
                        player.team == home_team
                        and player.starting_position == PositionType.Goalkeeper
                    ):
                        gk_x_positions.append(player_data.coordinates.x)
                        break

            if not gk_x_positions:
                continue

            # Calculate average GK x position
            avg_gk_x = sum(gk_x_positions) / len(gk_x_positions)

            # Home GK should always be on left (negative x) in every period
            if avg_gk_x > 0:
                raise ValueError(
                    f"CDF data orientation error: Home team goalkeeper "
                    f"found on right side (avg x={avg_gk_x:.2f}) in period {period.id}. "
                    f"CDF requires home team player left-to-right every period."
                )

    @classmethod
    def _frame_from_framedata(
        cls,
        teams: list[Team],
        team_by_id: dict[str, Team],
        period: Period,
        frame_data: dict,
        first_frame_timestamp: datetime,
    ):
        """Create a Frame from CDF frame data."""
        frame_id = frame_data["frame_id"]

        # Calculate timestamp relative to first frame of this period
        frame_timestamp_str = frame_data["timestamp"]
        frame_datetime = datetime.fromisoformat(frame_timestamp_str)
        frame_timestamp = timedelta(
            seconds=(frame_datetime - first_frame_timestamp).total_seconds()
        )

        # Ball coordinates (3D) - ball is required in CDF
        ball_data = frame_data["ball"]
        if ball_data["x"] is not None:
            ball_x = float(ball_data["x"])
            ball_y = float(ball_data["y"])
            ball_z = float(ball_data.get("z") or 0.0)
            ball_coordinates = Point3D(ball_x, ball_y, ball_z)
        else:
            ball_coordinates = None

        # Ball state
        ball_state = (
            BallState.ALIVE if frame_data["ball_status"] else BallState.DEAD
        )

        # Ball owning team (optional in CDF)
        ball_poss_team_id = frame_data.get("ball_poss_team_id")
        if ball_poss_team_id is not None:
            ball_owning_team = team_by_id.get(str(ball_poss_team_id))
        else:
            ball_owning_team = None

        # Build players_data from home and away teams
        players_data = {}
        teams_data = frame_data["teams"]

        for team, team_key in zip(teams, ["home", "away"]):
            team_frame_data = teams_data[team_key]
            players_list = team_frame_data["players"]

            for player_data in players_list:
                player_id = str(player_data["id"])
                player = team.get_player_by_id(player_id)

                if not player:
                    # Player not in metadata, create dynamically
                    position_code = player_data.get("position")
                    position = position_types_mapping.get(
                        position_code, PositionType.Unknown
                    )
                    player = Player(
                        player_id=player_id,
                        team=team,
                        starting_position=position,
                    )
                    team.players.append(player)

                x = float(player_data["x"])
                y = float(player_data["y"])
                players_data[player] = PlayerData(coordinates=Point(x, y))

        frame = create_frame(
            frame_id=frame_id,
            timestamp=frame_timestamp,
            ball_coordinates=ball_coordinates,
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            players_data=players_data,
            period=period,
            other_data={},
        )

        return frame

    def deserialize(self, inputs: CDFTrackingDataInputs) -> TrackingDataset:
        # Parse metadata JSON
        with performance_logging("Loading CDF metadata", logger=logger):
            metadata_content = json.loads(inputs.meta_data.read())

            # Extract required fields - fail fast on missing keys
            tracking_meta = metadata_content["meta"]["tracking"]
            frame_rate = tracking_meta["fps"]

            stadium = metadata_content["stadium"]
            pitch_length = float(stadium["pitch_length"])
            pitch_width = float(stadium["pitch_width"])

            match_data = metadata_content["match"]
            game_id = str(match_data["id"])
            kickoff_time_str = match_data.get("kickoff_time")
            if kickoff_time_str:
                date = datetime.fromisoformat(kickoff_time_str)
            else:
                date = None

            # Build periods
            periods = []
            for period_data in match_data["periods"]:
                period_name = period_data["period"]
                period_id = PERIOD_NAME_TO_ID.get(period_name)
                if period_id is None:
                    logger.warning(f"Unknown period name: {period_name}")
                    continue

                start_time_str = period_data.get("start_time")
                end_time_str = period_data.get("end_time")

                # Calculate period duration as timestamps
                if start_time_str and end_time_str:
                    start_dt = datetime.fromisoformat(start_time_str)
                    end_dt = datetime.fromisoformat(end_time_str)
                    start_timestamp = timedelta(seconds=0)
                    end_timestamp = timedelta(
                        seconds=(end_dt - start_dt).total_seconds()
                    )
                else:
                    start_timestamp = timedelta(seconds=0)
                    end_timestamp = timedelta(seconds=0)

                periods.append(
                    Period(
                        id=period_id,
                        start_timestamp=start_timestamp,
                        end_timestamp=end_timestamp,
                    )
                )

            # Build teams - require home and away keys
            teams_data = metadata_content["teams"]

            home_team_data = teams_data["home"]
            home_team = Team(
                team_id=str(home_team_data["id"]),
                name=home_team_data["name"],
                ground=Ground.HOME,
            )

            away_team_data = teams_data["away"]
            away_team = Team(
                team_id=str(away_team_data["id"]),
                name=away_team_data["name"],
                ground=Ground.AWAY,
            )

            # Add players to teams
            for team, team_data in [
                (home_team, home_team_data),
                (away_team, away_team_data),
            ]:
                for player_data in team_data["players"]:
                    player = Player(
                        player_id=str(player_data["id"]),
                        team=team,
                        jersey_no=player_data.get("jersey_number"),
                        starting=player_data.get("is_starter", False),
                    )
                    team.players.append(player)

            teams = [home_team, away_team]
            team_by_id = {team.team_id: team for team in teams}

        # Parse tracking JSONL
        with performance_logging("Loading CDF tracking data", logger=logger):
            transformer = self.get_transformer(
                pitch_length=pitch_length, pitch_width=pitch_width
            )

            period_map = {period.id: period for period in periods}

            # Read first frame for validation
            first_line = inputs.raw_data.readline()
            if isinstance(first_line, bytes):
                first_line = first_line.decode("utf-8")
            first_frame_data = json.loads(first_line.strip())

            # Validate CDF data
            self._validate_cdf_data(metadata_content, first_frame_data)

            # Reset to beginning and process all frames
            inputs.raw_data.seek(0)

            def _iter():
                n = 0
                sample = 1 / self.sample_rate

                for line in inputs.raw_data.readlines():
                    line = line.strip()
                    if not line:
                        continue

                    # Decode if bytes
                    if isinstance(line, bytes):
                        line = line.decode("utf-8")

                    frame_data = json.loads(line)

                    # Filter dead ball frames if only_alive is set
                    if self.only_alive and not frame_data["ball_status"]:
                        continue

                    # Filter empty frames if not including them
                    if not self.include_empty_frames:
                        teams_frame = frame_data["teams"]
                        home_players = teams_frame["home"]["players"]
                        away_players = teams_frame["away"]["players"]
                        if not home_players and not away_players:
                            continue

                    # Apply sampling
                    if n % sample == 0:
                        yield frame_data

                    n += 1

            frames = []
            n_frames = 0
            # Track first frame timestamp for each period (for relative timestamps)
            first_frame_timestamps: dict[int, datetime] = {}
            # Track if any frame has ball possession data
            has_ball_owning_team = False

            for frame_data in _iter():
                # Get period from frame
                period_name = frame_data["period"]
                period_id = PERIOD_NAME_TO_ID.get(period_name, 1)
                period = period_map.get(period_id)

                if period is None:
                    logger.warning(
                        f"Frame references unknown period: {period_name}"
                    )
                    continue

                # Track first frame timestamp for this period
                frame_datetime = datetime.fromisoformat(frame_data["timestamp"])
                if period_id not in first_frame_timestamps:
                    first_frame_timestamps[period_id] = frame_datetime

                # Check if this frame has ball possession data
                if frame_data.get("ball_poss_team_id") is not None:
                    has_ball_owning_team = True

                frame = self._frame_from_framedata(
                    teams,
                    team_by_id,
                    period,
                    frame_data,
                    first_frame_timestamps[period_id],
                )
                frame = transformer.transform_frame(frame)
                frames.append(frame)

                n_frames += 1

                if self.limit and n_frames >= self.limit:
                    break

        self._validate_orientation(frames, teams, periods)
        orientation = Orientation.STATIC_HOME_AWAY

        # Set flags based on available data
        flags = DatasetFlag.BALL_STATE
        if has_ball_owning_team:
            flags |= DatasetFlag.BALL_OWNING_TEAM

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=frame_rate,
            orientation=orientation,
            provider=Provider.CDF,
            flags=flags,
            coordinate_system=transformer.get_to_coordinate_system(),
            date=date,
            game_id=game_id,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
