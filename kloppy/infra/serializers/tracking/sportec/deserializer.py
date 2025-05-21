import logging
import warnings
from collections import defaultdict
from datetime import datetime, timedelta
from typing import IO, Dict, NamedTuple, Optional, Union

from lxml import etree, objectify

from kloppy.domain import (
    AttackingDirection,
    BallState,
    DatasetFlag,
    Metadata,
    Orientation,
    PlayerData,
    Point,
    Point3D,
    Provider,
    TrackingDataset,
    attacking_direction_from_frame,
)
from kloppy.domain.services.frame_factory import create_frame
from kloppy.infra.serializers.event.sportec.deserializer import (
    sportec_metadata_from_xml_elm,
)
from kloppy.utils import performance_logging

from ..deserializer import TrackingDataDeserializer

logger = logging.getLogger(__name__)

GAME_SECTION_TO_PERIOD_ID = {
    "firstHalf": 1,
    "secondHalf": 2,
    "firstHalfExtra": 3,
    "secondHalfExtra": 4,
}


def _unstack_framesets(
    raw_data: IO[bytes],
    limit: Optional[int] = None,
    only_alive: Optional[bool] = True,
) -> Dict[int, Dict[int, Dict]]:
    """
    Read all data and unstack framesets.

    If a limit is given, will only parse the first `limit` frames
    for each object.

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
    if not limit:
        limit = float("inf")

    raw_frames = defaultdict(lambda: defaultdict(dict))
    frames_per_obj = defaultdict(int)
    current_period = None
    current_obj = None

    context = etree.iterparse(
        raw_data, events=("start", "end"), huge_tree=True
    )

    for event, elem in context:
        try:
            if event == "start" and elem.tag == "FrameSet":
                game_section = elem.get("GameSection")
                if game_section in GAME_SECTION_TO_PERIOD_ID:
                    # Do we still need to process this game section?
                    if (
                        current_period is not None
                        and current_period
                        != GAME_SECTION_TO_PERIOD_ID[game_section]
                        and all(n > limit for n in frames_per_obj.values())
                    ):
                        break

                    current_period = GAME_SECTION_TO_PERIOD_ID[game_section]
                    current_obj = (
                        "ball"
                        if elem.get("TeamId") == "BALL"
                        else elem.get("PersonId")
                    )
            elif event == "start" and elem.tag == "Frame":
                if (
                    current_period
                    and current_obj
                    and (int(elem.get("BallStatus", 0)) == 1 or not only_alive)
                    and frames_per_obj.get(current_obj, 0) < limit
                ):
                    frames_per_obj[current_obj] += 1
                    frame_id = int(elem.get("N"))
                    raw_frames[current_period][frame_id][current_obj] = {
                        k: v for k, v in elem.items()
                    }
                elem.clear()
            elif event == "end" and elem.tag == "FrameSet":
                elem.clear()
        finally:
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

    return dict(raw_frames)


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
        with performance_logging("parse metadata", logger=logger):
            match_root = objectify.fromstring(inputs.meta_data.read())
            sportec_metadata = sportec_metadata_from_xml_elm(match_root)
            teams = home_team, away_team = sportec_metadata.teams
            date = datetime.fromisoformat(
                match_root.MatchInformation.General.attrib["KickoffTime"]
            )
            game_week = match_root.MatchInformation.General.attrib["MatchDay"]
            game_id = match_root.MatchInformation.General.attrib["MatchId"]

            periods = sportec_metadata.periods
            transformer = self.get_transformer(
                pitch_length=sportec_metadata.x_max,
                pitch_width=sportec_metadata.y_max,
            )

        # Stream and process tracking data
        with performance_logging("parse tracking data", logger=logger):
            limit = self.limit
            if self.sample_rate:
                limit = int(limit / self.sample_rate) if limit else None
            period_frames = _unstack_framesets(
                inputs.raw_data, limit, self.only_alive
            )
            player_map = {
                player.player_id: player
                for team in teams
                for player in team.players
            }
            official_ids = {
                official.official_id
                for official in (sportec_metadata.officials or [])
            }

            frames = []
            sample = 1.0 / self.sample_rate if self.sample_rate else 1
            frame_count = 0

            for period in periods:
                period_id = period.id
                raw_period_frames = period_frames.get(period_id, {})

                sorted_frame_ids = sorted(raw_period_frames.keys())
                for i, frame_id in enumerate(sorted_frame_ids):
                    if self.limit and frame_count >= self.limit:
                        break

                    frame_data = raw_period_frames[frame_id]
                    if "ball" not in frame_data:
                        continue

                    ball_data = frame_data["ball"]
                    if self.only_alive and ball_data.get("BallStatus") != "1":
                        continue

                    if i % sample != 0:
                        continue

                    try:
                        frame = create_frame(
                            frame_id=frame_id,
                            timestamp=timedelta(
                                seconds=(
                                    frame_id
                                    - period.start_timestamp.seconds
                                    * sportec_metadata.fps
                                )
                                / sportec_metadata.fps
                            ),
                            ball_owning_team=home_team
                            if ball_data.get("BallPossession") == "1"
                            else away_team,
                            ball_state=BallState.ALIVE
                            if ball_data.get("BallStatus") == "1"
                            else BallState.DEAD,
                            period=period,
                            players_data={
                                player_map[player_id]: PlayerData(
                                    coordinates=Point(
                                        x=float(data.get("X", 0)),
                                        y=float(data.get("Y", 0)),
                                    ),
                                    speed=float(data.get("S", 0)),
                                )
                                for player_id, data in frame_data.items()
                                if player_id != "ball"
                                and player_id not in official_ids
                                and player_id in player_map
                            },
                            ball_coordinates=Point3D(
                                x=float(ball_data.get("X", 0)),
                                y=float(ball_data.get("Y", 0)),
                                z=float(ball_data.get("Z", 0)),
                            ),
                            ball_speed=float(ball_data.get("S", 0)),
                            other_data={},
                        )
                        frames.append(transformer.transform_frame(frame))
                        frame_count += 1
                    except KeyError as e:
                        logger.warning(
                            f"Skipping frame {frame_id} due to missing data: {e}"
                        )

        # Determine orientation
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
            orientation = Orientation.NOT_SET
            warnings.warn("Could not determine dataset orientation")

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
            date=date,
            game_week=game_week,
            game_id=game_id,
            home_coach=sportec_metadata.home_coach,
            away_coach=sportec_metadata.away_coach,
            officials=sportec_metadata.officials,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
