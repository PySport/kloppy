import logging
from datetime import timedelta
import warnings
from typing import IO, NamedTuple, Optional, Union


from kloppy.domain import (
    AttackingDirection,
    BallState,
    DatasetFlag,
    Frame,
    Metadata,
    Orientation,
    Player,
    PlayerData,
    Point,
    Point3D,
    Provider,
    TrackingDataset,
    attacking_direction_from_frame,
)
from kloppy.utils import performance_logging
from kloppy.infra.serializers.event.statsperform.parsers import get_parser

from .deserializer import TrackingDataDeserializer

logger = logging.getLogger(__name__)


class StatsPerformInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]
    pitch_length: Optional[float] = None
    pitch_width: Optional[float] = None


class StatsPerformDeserializer(TrackingDataDeserializer[StatsPerformInputs]):
    def __init__(
        self,
        provider: Provider,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: Optional[bool] = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive
        self._provider = provider

    @property
    def provider(self) -> Provider:
        return self._provider

    @classmethod
    def __get_frame_rate(cls, tracking):
        """Infer the frame rate of the tracking data."""

        frame_numbers = [
            int(line.split(";")[1].split(",")[0]) for line in tracking[1:]
        ]

        deltas = [
            frame_numbers[i + 1] - frame_numbers[i]
            for i in range(len(frame_numbers) - 1)
        ]

        most_common_delta = max(set(deltas), key=deltas.count)
        frame_rate = 1000 / most_common_delta

        return frame_rate

    @classmethod
    def _frame_from_framedata(cls, teams_list, period, frame_data):
        components = frame_data[1].split(":")
        frame_info = components[0].split(";")

        frame_id = int(frame_info[0])
        frame_timestamp = timedelta(
            seconds=int(frame_info[1].split(",")[0]) / 1000
        )
        match_status = int(frame_info[1].split(",")[2])

        ball_state = BallState.ALIVE if match_status == 0 else BallState.DEAD

        if len(components) > 2:
            ball_data = components[2].split(";")[0].split(",")
            ball_x, ball_y, ball_z = map(float, ball_data)
            ball_coordinates = Point3D(ball_x, ball_y, ball_z)
        else:
            ball_coordinates = None

        players_data = {}
        player_info = components[1].split(";")[:-1]
        for player_data in player_info:
            player_data = player_data.split(",")

            team_side_id = int(player_data[0])
            player_id = player_data[1]
            jersey_no = int(player_data[2])
            x = float(player_data[3])
            y = float(player_data[4])

            # Goalkeepers have id 3 and 4
            if team_side_id > 2:
                team_side_id = team_side_id - 3
            team = teams_list[team_side_id]
            player = team.get_player_by_id(player_id)

            if not player:
                player = Player(
                    player_id=player_id,
                    team=team,
                    jersey_no=jersey_no,
                )
                team.players.append(player)

            players_data[player] = PlayerData(coordinates=Point(x, y))

        return Frame(
            frame_id=frame_id,
            timestamp=frame_timestamp,
            ball_coordinates=ball_coordinates,
            ball_state=ball_state,
            ball_owning_team=None,
            players_data=players_data,
            period=period,
            other_data={},
        )

    def deserialize(self, inputs: StatsPerformInputs) -> TrackingDataset:
        with performance_logging("Loading meta data", logger=logger):
            meta_data_parser = get_parser(inputs.meta_data, "MA1")

            periods = {
                period.id: period
                for period in meta_data_parser.extract_periods()
            }
            teams_list = list(meta_data_parser.extract_lineups())

        with performance_logging("Loading tracking data", logger=logger):
            tracking_data = inputs.raw_data.read().decode("ascii").splitlines()
            frame_rate = self.__get_frame_rate(tracking_data)

            transformer = self.get_transformer(
                pitch_length=inputs.pitch_length,
                pitch_width=inputs.pitch_width,
            )

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for line_ in tracking_data:
                    splits = line_.split(";")[1].split(",")
                    period_id = int(splits[1])
                    period_ = periods[period_id]
                    if n % sample == 0:
                        yield period_, line_
                    n += 1

            frames = []
            for n, frame_data in enumerate(_iter(), start=1):
                period = frame_data[0]
                frame = self._frame_from_framedata(
                    teams_list, period, frame_data
                )
                frame = transformer.transform_frame(frame)
                if self.only_alive and frame.ball_state == BallState.DEAD:
                    continue
                frames.append(frame)

                if self.limit and n >= self.limit:
                    break

        try:
            first_frame = next(
                frame for frame in frames if frame.period.id == 1
            )
            orientation = (
                Orientation.HOME_AWAY
                if attacking_direction_from_frame(first_frame)
                == AttackingDirection.LTR
                else Orientation.AWAY_HOME
            )
        except StopIteration:
            warnings.warn(
                "Could not determine orientation of dataset, defaulting to NOT_SET"
            )
            orientation = Orientation.NOT_SET

        meta_data = Metadata(
            teams=teams_list,
            periods=list(periods.values()),
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=None,
            frame_rate=frame_rate,
            orientation=orientation,
            provider=Provider.STATSPERFORM,
            flags=DatasetFlag.BALL_STATE,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return TrackingDataset(
            records=frames,
            metadata=meta_data,
        )
