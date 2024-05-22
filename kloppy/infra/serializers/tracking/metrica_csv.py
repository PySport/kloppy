import logging
import warnings
from collections import namedtuple
from datetime import timedelta
from typing import Tuple, Dict, Iterator, IO, NamedTuple

from kloppy.domain import (
    attacking_direction_from_frame,
    TrackingDataset,
    AttackingDirection,
    Frame,
    Point,
    Period,
    Orientation,
    Provider,
    DatasetFlag,
    Metadata,
    Team,
    Ground,
    Player,
    PlayerData,
)
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.utils import Readable, performance_logging


logger = logging.getLogger(__name__)


class MetricaCSVTrackingDataInputs(NamedTuple):
    home_data: IO[bytes]
    away_data: IO[bytes]


class MetricaCSVTrackingDataDeserializer(
    TrackingDataDeserializer[MetricaCSVTrackingDataInputs]
):
    __PartialFrame = namedtuple(
        "PartialFrame",
        "team period frame_id players_data ball_coordinates",
    )

    @property
    def provider(self) -> Provider:
        return Provider.METRICA

    def __create_iterator(
        self,
        data: IO[bytes],
        sample_rate: float,
        frame_rate: int,
        ground: Ground,
    ) -> Iterator:
        """
        Notes:
            1. the y-axis is flipped because Metrica use (y, -y) instead of (-y, y)
        """

        team = None
        frame_idx = 0
        frame_sample = 1 / sample_rate
        player_jersey_numbers = []
        period = None

        for i, line in enumerate(data):
            line = line.strip().decode("ascii")
            columns = line.split(",")
            if i == 0:
                team_name = columns[3]
                team = Team(team_id=str(ground), name=team_name, ground=ground)
            elif i == 1:
                player_jersey_numbers = columns[3:-2:2]
                players = [
                    Player(
                        player_id=f"{team.ground}_{jersey_number}",
                        jersey_no=int(jersey_number),
                        team=team,
                    )
                    for jersey_number in player_jersey_numbers
                ]
                team.players = players
            elif i == 2:
                # consider doing some validation on the columns
                pass
            else:
                period_id = int(columns[0])
                frame_id = int(columns[1])

                if period is None or period.id != period_id:
                    period = Period(
                        id=period_id,
                        start_timestamp=timedelta(
                            seconds=(frame_id - 1) / frame_rate
                        ),
                        end_timestamp=timedelta(seconds=frame_id / frame_rate),
                    )
                else:
                    # consider not update this every frame for performance reasons
                    period.end_timestamp = timedelta(
                        seconds=frame_id / frame_rate
                    )

                if frame_idx % frame_sample == 0:
                    yield self.__PartialFrame(
                        team=team,
                        period=period,
                        frame_id=frame_id,
                        players_data={
                            player: PlayerData(
                                coordinates=Point(
                                    x=float(columns[3 + i * 2]),
                                    y=1 - float(columns[3 + i * 2 + 1]),
                                )
                            )
                            for i, player in enumerate(players)
                            if columns[3 + i * 2] != "NaN"
                        },
                        ball_coordinates=Point(
                            x=float(columns[-2]), y=1 - float(columns[-1])
                        )
                        if columns[-2] != "NaN"
                        else None,
                    )
                frame_idx += 1

    @staticmethod
    def __validate_partials(
        home_partial_frame: __PartialFrame, away_partial_frame: __PartialFrame
    ):
        if home_partial_frame.frame_id != away_partial_frame.frame_id:
            raise ValueError(
                f"frame_id mismatch: home {home_partial_frame.frame_id}, "
                f"away: {away_partial_frame.frame_id}"
            )
        if (
            home_partial_frame.ball_coordinates
            != away_partial_frame.ball_coordinates
        ):
            raise ValueError(
                f"ball position mismatch: home {home_partial_frame.ball_coordinates}, "
                f"away: {away_partial_frame.ball_coordinates}. Do the files belong to the"
                f" same game? frame_id: {home_partial_frame.frame_id}"
            )
        if home_partial_frame.team.ground != Ground.HOME:
            raise ValueError("raw_data_home contains away team data")
        if away_partial_frame.team.ground != Ground.AWAY:
            raise ValueError("raw_data_away contains home team data")

    def deserialize(
        self, inputs: MetricaCSVTrackingDataInputs
    ) -> TrackingDataset:
        # consider reading this from data
        frame_rate = 25

        transformer = self.get_transformer()

        with performance_logging("prepare", logger=logger):
            home_iterator = self.__create_iterator(
                inputs.home_data, self.sample_rate, frame_rate, Ground.HOME
            )
            away_iterator = self.__create_iterator(
                inputs.away_data, self.sample_rate, frame_rate, Ground.AWAY
            )

            partial_frames = zip(home_iterator, away_iterator)

        with performance_logging("loading", logger=logger):
            frames = []
            periods = []

            partial_frame_type = self.__PartialFrame
            home_partial_frame: partial_frame_type
            away_partial_frame: partial_frame_type
            for n, (home_partial_frame, away_partial_frame) in enumerate(
                partial_frames
            ):
                self.__validate_partials(
                    home_partial_frame, away_partial_frame
                )

                period: Period = home_partial_frame.period
                frame_id: int = home_partial_frame.frame_id

                players_data = {
                    **home_partial_frame.players_data,
                    **away_partial_frame.players_data,
                }

                frame = Frame(
                    frame_id=frame_id,
                    timestamp=timedelta(seconds=frame_id / frame_rate)
                    - period.start_timestamp,
                    ball_coordinates=home_partial_frame.ball_coordinates,
                    players_data=players_data,
                    period=period,
                    ball_state=None,
                    ball_owning_team=None,
                    other_data={},
                )

                frame = transformer.transform_frame(frame)

                frames.append(frame)

                if not periods or period.id != periods[-1].id:
                    periods.append(period)

                if n == 0:
                    teams = [home_partial_frame.team, away_partial_frame.team]

                n += 1
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

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=None,
            frame_rate=frame_rate,
            orientation=orientation,
            provider=Provider.METRICA,
            flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return TrackingDataset(records=frames, metadata=metadata)
