import logging
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


def elem2dict(node):
    """Convert an lxml.etree node tree into a dict."""
    return dict(node.items())


def any_of(*predicates: Callable[..., bool]) -> Callable[..., bool]:
    """
    Return a new function that is True if ANY of the given predicates are True.
    """

    def combined(*args, **kwargs) -> bool:
        return any(pred(*args, **kwargs) for pred in predicates)

    return combined


def all_of(*predicates: Callable[..., bool]) -> Callable[..., bool]:
    """
    Return a new function that is True if ALL of the given predicates are True.
    """

    def combined(*args, **kwargs) -> bool:
        return all(pred(*args, **kwargs) for pred in predicates)

    return combined


def _unstack_framesets(
    raw_data: IO[bytes],
    limit: Optional[int] = None,
    only_alive: bool = True,
    objects_to_skip: Optional[Set[str]] = None,
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
        skip_frameset: Optional[Callable[[int, str], bool]] = None,
        end_frameset: Optional[Callable[[int, str], bool]] = None,
        skip_frame: Optional[
            Callable[[int, str, Dict[str, str]], bool]
        ] = None,
    ) -> None:
        """Generic pass over the XML to collect frames.

        Args:
            skip_framset: A callable that returns True when the parsing should skip a frameset.
            end_frameset: A callable that returns True when the frameset should be ended.
            skip_frame: A callable that returns True when a frame should be skipped.
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
                current_period = GAME_SECTION_TO_PERIOD_ID.get(section)
                if current_period is None:
                    logger.warning(
                        "Found FrameSet with unknown or missing period: %s",
                        elem2dict(elem),
                    )
                    continue
                current_obj = (
                    "ball"
                    if elem.get("TeamId") == "BALL"
                    else elem.get("PersonId")
                )
                if current_obj is None:
                    logger.warning(
                        "Found FrameSet with unknown or missing object ID: %s",
                        elem2dict(elem),
                    )
                    continue
                if skip_frameset is not None and skip_frameset(
                    current_period, current_obj
                ):
                    current_period = None
                    current_obj = None
                    continue
                logger.debug(
                    "Processing FrameSet for object %s in period %s",
                    current_obj,
                    current_period,
                )

            elif (
                event == "start"
                and elem.tag == "Frame"
                and current_period is not None
                and current_obj is not None
            ):
                frame_data = elem2dict(elem)
                if skip_frame is not None and skip_frame(
                    current_period, current_obj, frame_data
                ):
                    continue
                if "N" not in frame_data:
                    logger.warning(
                        "Found Frame with missing ID: %s",
                        frame_data,
                    )
                    continue
                fid = int(frame_data["N"])
                frames[current_period][fid][current_obj] = elem2dict(elem)
                frames_per_obj[current_obj] += 1
                if end_frameset is not None and end_frameset(
                    current_period, current_obj
                ):
                    current_period = None
                    current_obj = None

            # Always clear elements to save memory
            elif event == "end" and elem.tag in ("Frame", "FrameSet"):
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

    def make_object_filter(
        objects: Set[str],
        include: bool = True,
    ) -> Callable[[int, str], bool]:
        """
        Returns a callable that checks if the current object should be skipped
        based on membership in the given set.

        Args:
            objects: Set of object names to include/exclude.
            include: If True, only allow objects IN the set. If False, exclude objects IN the set.
        """

        def _filter(current_period: int, current_obj: str) -> bool:
            skip = (
                (current_obj not in objects)
                if include
                else (current_obj in objects)
            )
            if skip:
                logger.debug(
                    "Skipping FrameSet for object %s in period %s (reason: %s objects=%s)",
                    current_obj,
                    current_period,
                    ("not in" if include else "in"),
                    objects,
                )
            return skip

        return _filter

    def check_limit(current_period: int, current_obj: str) -> bool:
        """
        Check if the limit has been reached for the current object.
        """
        assert limit is not None
        skip = frames_per_obj.get(current_obj, 0) >= limit
        if skip:
            logger.debug(
                "Reached limit=%d for object %s in period %s",
                frames_per_obj.get(current_obj, 0),
                current_obj,
                current_period,
            )
        return skip

    def check_only_alive(
        current_period: int, current_obj: str, frame_data: Dict[str, str]
    ) -> bool:
        """
        Check if the ball is out of play in the current frame.
        """
        assert only_alive is True
        fid = int(frame_data.get("N", 0))

        if current_obj == "ball":
            skip = int(frame_data.get(BALL_STATUS, "0")) != 1
        else:
            skip = "ball" not in frames.get(current_period, {}).get(fid, {})

        if skip:
            logger.debug(
                "Skipping Frame %d for object %s in period %s (reason: ball not in play)",
                fid,
                current_obj,
                current_period,
            )
        return skip

    # --- Build predicates dynamically ---

    skip_frameset = make_object_filter(objects_to_skip, include=False)
    skip_frameset_ball = make_object_filter({"ball"}, include=True)
    skip_frameset_players = make_object_filter(
        objects_to_skip | {"ball"}, include=False
    )

    if limit:
        skip_frameset = any_of(skip_frameset, check_limit)
        skip_frameset_ball = any_of(skip_frameset_ball, check_limit)
        skip_frameset_players = any_of(skip_frameset_players, check_limit)

    end_frameset = check_limit if limit else None
    skip_frame = check_only_alive if only_alive else None

    # --- Processing passes ---

    if only_alive:
        # First pass: only the ball to get the frames where the ball is alive
        _make_pass(
            skip_frameset=skip_frameset_ball,
            end_frameset=end_frameset,
            skip_frame=skip_frame,
        )
        # Second pass: all other objects in these frames
        _make_pass(
            skip_frameset=skip_frameset_players,
            end_frameset=end_frameset,
            skip_frame=skip_frame,
        )
    else:
        _make_pass(
            skip_frameset=skip_frameset,
            end_frameset=end_frameset,
            skip_frame=skip_frame,
        )

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
                limit=(
                    int(self.limit / self.sample_rate)
                    if self.sample_rate and self.limit
                    else self.limit
                ),
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
                            ball_owning_team=(
                                home_team
                                if int(ball_data.get(BALL_POSSESSION, 0)) == 1
                                else away_team
                            ),
                            ball_state=(
                                BallState.ALIVE
                                if int(ball_data.get(BALL_STATUS, 0)) == 1
                                else BallState.DEAD
                            ),
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
