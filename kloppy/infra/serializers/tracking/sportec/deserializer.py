import logging
import warnings
from collections import defaultdict
from typing import NamedTuple, Optional, Union, IO
from datetime import timedelta

from lxml import objectify

from kloppy.domain import (
    TrackingDataset,
    DatasetFlag,
    AttackingDirection,
    Frame,
    Point,
    Point3D,
    BallState,
    Period,
    Orientation,
    attacking_direction_from_frame,
    Metadata,
    Provider,
    PlayerData,
)

from kloppy.utils import performance_logging

from ..deserializer import TrackingDataDeserializer
from kloppy.infra.serializers.event.sportec.deserializer import (
    sportec_metadata_from_xml_elm,
)

logger = logging.getLogger(__name__)

PERIOD_ID_TO_GAME_SECTION = {
    1: "firstHalf",
    2: "secondHalf",
    3: "firstHalfExtra",
    4: "secondHalfExtra",
}


def _read_section_data(data_root, period: Period) -> dict:
    """
    Read all data for a single period from data_root.

    Output format:
    {
        10_000: {
            'ball': {
                'N': "10000",
                'X': 20.92,
                'Y': 2.84,
                'Z': 0.08,
                'S': 4.91,
                'BallPossession': "2",
                'BallStatus': "1"
                [...]
            },
            'DFL-OBJ-002G3I': {
                'N': "10000",
                'X': "0.35",
                'Y': "-25.26",
                'S': "0.00",
                [...]
            },
            [....]
        },
        10_001: {
          ...
        }
    }
    """

    game_section = PERIOD_ID_TO_GAME_SECTION[period.id]
    frame_sets = data_root.findall(
        f"Positions/FrameSet[@GameSection='{game_section}']"
    )

    raw_frames = defaultdict(dict)
    for frame_set in frame_sets:
        key = (
            "ball"
            if frame_set.attrib["TeamId"] == "BALL"
            else frame_set.attrib["PersonId"]
        )
        for frame in frame_set.iterchildren("Frame"):
            attr = frame.attrib
            frame_id = int(attr["N"])
            raw_frames[frame_id][key] = attr

    return raw_frames


class SportecTrackingDataInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class SportecTrackingDataDeserializer(TrackingDataDeserializer):
    @property
    def provider(self) -> Provider:
        return Provider.SPORTEC

    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: Optional[bool] = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive

    def deserialize(
        self, inputs: SportecTrackingDataInputs
    ) -> TrackingDataset:
        with performance_logging("load data", logger=logger):
            match_root = objectify.fromstring(inputs.meta_data.read())
            data_root = objectify.fromstring(inputs.raw_data.read())

        with performance_logging("parse metadata", logger=logger):
            sportec_metadata = sportec_metadata_from_xml_elm(match_root)
            teams = home_team, away_team = sportec_metadata.teams
            periods = sportec_metadata.periods
            transformer = self.get_transformer(
                length=sportec_metadata.x_max, width=sportec_metadata.y_max
            )

        with performance_logging("parse raw data", logger=logger):

            def _iter():
                player_map = {}
                for player in home_team.players:
                    player_map[player.player_id] = player
                for player in away_team.players:
                    player_map[player.player_id] = player

                sample = 1.0 / self.sample_rate

                for period in periods:
                    raw_frames = _read_section_data(data_root, period)

                    # Since python 3.6 dict keep insertion order. Don't need to sort
                    # on frame ID as it's already sorted.
                    # Ball FrameSet is always first and contains ALL frame ids. This
                    # makes sure even with substitutes the data is on order.
                    for i, (frame_id, frame_data) in enumerate(
                        sorted(raw_frames.items())
                    ):
                        if "ball" not in frame_data:
                            # Frames without ball data are corrupt.
                            continue

                        ball_data = frame_data["ball"]
                        if self.only_alive and ball_data["BallStatus"] != "1":
                            continue

                        if i % sample == 0:
                            yield Frame(
                                frame_id=frame_id,
                                timestamp=timedelta(
                                    seconds=(
                                        frame_id
                                        # Do subtraction with integers to prevent floating errors
                                        - period.start_timestamp.seconds
                                        * sportec_metadata.fps
                                    )
                                    / sportec_metadata.fps
                                ),
                                ball_owning_team=home_team
                                if ball_data["BallPossession"] == "1"
                                else away_team,
                                ball_state=BallState.ALIVE
                                if ball_data["BallStatus"] == "1"
                                else BallState.DEAD,
                                period=period,
                                players_data={
                                    player_map[player_id]: PlayerData(
                                        coordinates=Point(
                                            x=float(raw_player_data["X"]),
                                            y=float(raw_player_data["Y"]),
                                        ),
                                        speed=float(raw_player_data["S"]),
                                    )
                                    for player_id, raw_player_data in frame_data.items()
                                    if player_id != "ball"
                                },
                                other_data={},
                                ball_coordinates=Point3D(
                                    x=float(ball_data["X"]),
                                    y=float(ball_data["Y"]),
                                    z=float(ball_data["Z"]),
                                ),
                                ball_speed=float(ball_data["S"]),
                            )

            frames = []
            for n, frame in enumerate(_iter()):
                frame = transformer.transform_frame(frame)
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

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=sportec_metadata.score,
            frame_rate=sportec_metadata.fps,
            orientation=orientation,
            provider=Provider.SPORTEC,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
