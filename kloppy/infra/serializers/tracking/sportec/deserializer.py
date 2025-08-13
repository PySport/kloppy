import logging
import warnings
from collections import defaultdict
from datetime import datetime, timedelta
from typing import IO, Callable, Dict, NamedTuple, Optional, Set, Union

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

BALL_STATUS = "BallStatus"
BALL_POSSESSION = "BallPossession"

GAME_SECTION_TO_PERIOD_ID = {
    "firstHalf": 1,
    "secondHalf": 2,
    "firstHalfExtra": 3,
    "secondHalfExtra": 4,
}


def _unstack_framesets(
    raw_data: IO[bytes],
    limit: Optional[int] = None,
    only_alive: bool = True,
    objects_to_skip: Optional[Set] = None,
) -> Dict[int, Dict[int, Dict]]:
    """Unstack framesets.

    Sportec groups frames per period and object in a frameset. This function
    unstacks the framesets and returns a nested dict:

        { period: { frame_id: { object_id: {attr: value, ...}, ...}, ...}, ... }

    Args:
        raw_data: The raw XML data stream to be parsed.
        limit: Max frames to collect.
        only_alive: Only include frames where BALL_STATUS == "1".
        objects_to_skip: A set of object IDs to skip.

    Returns:
        A nested dict period → frame_id → object_id → attributes.

    Notes:
        This function assumes that the framesets are ordered by period and
        that the frames in each frameset are ordered.
    """
    objects_to_skip = objects_to_skip or set()
    frames: Dict[int, Dict[int, Dict[str, Dict[str, str]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    frames_per_obj: Dict[str, int] = defaultdict(int)

    def _make_pass(
        stop_predicate: Callable[[], bool],
        skip_predicate: Callable[[etree.Element, int, str], bool],
    ) -> None:
        """Generic pass over the XML to collect frames.

        Args:
            stop_predicate: A callable that returns True when the parsing should stop
                for the first frameset of a new period.
            skip_predicate: A callable that returns True when a frame should be skipped.
        """
        raw_data.seek(0)
        context = etree.iterparse(
            raw_data, events=("start", "end"), huge_tree=True
        )
        current_period = None
        current_obj = None

        for event, elem in context:
            if event == "start" and elem.tag == "FrameSet":
                section = elem.get("GameSection")
                if section in GAME_SECTION_TO_PERIOD_ID:
                    new_period = GAME_SECTION_TO_PERIOD_ID[section]
                    # break if we've moved to a new period and stop_predicate says so
                    if (
                        current_period is not None
                        and new_period != current_period
                        and stop_predicate()
                    ):
                        break

                    current_period = new_period
                    # decide which object this frameset belongs to
                    current_obj = (
                        "ball"
                        if elem.get("TeamId") == "BALL"
                        else elem.get("PersonId")
                    )

            elif (
                event == "start"
                and elem.tag == "Frame"
                and current_period is not None
                and current_obj is not None
                and not skip_predicate(elem, current_period, current_obj)
            ):
                fid = int(elem.get("N"))
                frames[current_period][fid][current_obj] = dict(elem.items())
                frames_per_obj[current_obj] += 1

            # Always clear elements to save memory
            elif event == "end" and elem.tag in ("Frame", "FrameSet"):
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

    # First pass: only ball
    def stop_ball() -> bool:
        """
        Stop if a `limit` is set and we have already collected
        at least `limit` frames for the ball
        """
        return bool(limit) and frames_per_obj.get("ball", 0) >= limit

    def skip_ball(
        elem: etree.Element, current_period: int, current_obj: str
    ) -> bool:
        """
        Skip if any of the following is true:
          1. The frame does not belong to the ball.
          2. We only want “alive” frames and this one isn’t BALL_STATUS == 1.
          3. A `limit` is set and we already hit that limit for the ball.
        """
        return (
            (current_obj != "ball")
            or (only_alive and int(elem.get(BALL_STATUS, "0")) != 1)
            or (bool(limit) and frames_per_obj.get("ball", 0) >= limit)
        )

    _make_pass(stop_predicate=stop_ball, skip_predicate=skip_ball)

    # Second pass: all other objects
    objects_to_skip.add("ball")

    def stop_players() -> bool:
        """
        Stop if a non‐zero `limit` is set and *every* non‐skipped object
        has already collected at least `limit` frames.
        """
        return limit is not None and all(
            count >= limit
            for obj, count in frames_per_obj.items()
            if obj not in objects_to_skip
        )

    def skip_players(
        elem: etree.Element, current_period: int, current_obj: str
    ):
        """
        Skip if any of the following is true:
          1. The object is in `objects_to_skip` (including “ball”).
          2. A non‐zero `limit` is set and we already hit it for this object.
          3. We only want "alive" ball frames, and this frame occurs at a
             moment when the ball isn’t alive (so the player frame is irrelevant).
        """
        fid = int(elem.get("N"))
        return (
            (current_obj in objects_to_skip)
            or (bool(limit) and frames_per_obj[current_obj] >= limit)
            or (
                only_alive
                and "ball" not in frames.get(current_period, {}).get(fid, {})
            )
        )

    _make_pass(stop_predicate=stop_players, skip_predicate=skip_players)

    return dict(frames)


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
        only_alive: bool = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive

    def deserialize(
        self, inputs: SportecTrackingDataInputs
    ) -> TrackingDataset:
        with performance_logging("parse metadata", logger=logger):
            match_root = objectify.fromstring(inputs.meta_data.read())
            sportec_metadata = sportec_metadata_from_xml_elm(match_root)
            date = datetime.fromisoformat(
                match_root.MatchInformation.General.attrib["KickoffTime"]
            )
            game_week = match_root.MatchInformation.General.attrib["MatchDay"]
            game_id = match_root.MatchInformation.General.attrib["MatchId"]
            periods = sportec_metadata.periods
            teams = home_team, away_team = sportec_metadata.teams
            player_map = {
                player.player_id: player
                for team in teams
                for player in team.players
            }
            official_ids = {
                official.official_id
                for official in (sportec_metadata.officials or [])
            }

            transformer = self.get_transformer(
                pitch_length=sportec_metadata.x_max,
                pitch_width=sportec_metadata.y_max,
            )

        # Stream and process tracking data
        with performance_logging("parse tracking data", logger=logger):
            period_frames = _unstack_framesets(
                inputs.raw_data,
                limit=int(self.limit / self.sample_rate)
                if self.sample_rate and self.limit
                else self.limit,
                only_alive=self.only_alive,
                objects_to_skip=official_ids,
            )

            frames = []
            sample = 1.0 / self.sample_rate if self.sample_rate else 1
            frame_count = 0

            for period in periods:
                raw_period_frames = period_frames.get(period.id, {})

                sorted_frame_ids = sorted(raw_period_frames.keys())
                for (
                    i,
                    frame_id,
                ) in enumerate(sorted_frame_ids):
                    if self.limit and frame_count >= self.limit:
                        break

                    frame_data = raw_period_frames[frame_id]
                    if "ball" not in frame_data:
                        continue

                    ball_data = frame_data.get("ball", {})
                    if (
                        self.only_alive
                        and int(ball_data.get(BALL_STATUS, 0)) != 1
                    ):
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
                            if int(ball_data.get(BALL_POSSESSION, 0)) == 1
                            else away_team,
                            ball_state=BallState.ALIVE
                            if int(ball_data.get(BALL_STATUS, 0)) == 1
                            else BallState.DEAD,
                            period=period,
                            players_data={
                                player_map[object_id]: PlayerData(
                                    coordinates=Point(
                                        x=float(data.get("X", 0)),
                                        y=float(data.get("Y", 0)),
                                    ),
                                    speed=float(data.get("S", 0)),
                                )
                                for object_id, data in frame_data.items()
                                if object_id != "ball"
                                and object_id not in official_ids
                                and object_id in player_map
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
            logger.warning("Could not determine dataset orientation")

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
