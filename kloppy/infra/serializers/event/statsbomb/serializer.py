from typing import Tuple, Dict, List
import logging
import json

from kloppy.domain import (
    EventDataset,
    Team,
    Period,
    Point,
    BallState,
    DatasetFlag,
    Orientation,
    PitchDimensions,
    Dimension,
    PassEvent,
    ShotEvent,
    TakeOnEvent,
    CarryEvent,
    GenericEvent,
    PassResult,
    ShotResult,
    TakeOnResult,
    CarryResult,
    EventType,
)
from kloppy.infra.serializers.event import EventDataSerializer
from kloppy.infra.utils import Readable, performance_logging

logger = logging.getLogger(__name__)


SB_EVENT_TYPE_DRIBBLE = 14
SB_EVENT_TYPE_SHOT = 16
SB_EVENT_TYPE_PASS = 30
SB_EVENT_TYPE_CARRY = 43

SB_EVENT_TYPE_HALF_START = 18
SB_EVENT_TYPE_HALF_END = 34

SB_PASS_OUTCOME_COMPLETE = 8
SB_PASS_OUTCOME_INCOMPLETE = 9
SB_PASS_OUTCOME_INJURY_CLEARANCE = 74
SB_PASS_OUTCOME_OUT = 75
SB_PASS_OUTCOME_OFFSIDE = 76
SB_PASS_OUTCOME_UNKNOWN = 77

SB_SHOT_OUTCOME_BLOCKED = 96
SB_SHOT_OUTCOME_GOAL = 97
SB_SHOT_OUTCOME_OFF_TARGET = 98
SB_SHOT_OUTCOME_POST = 99
SB_SHOT_OUTCOME_SAVED = 100
SB_SHOT_OUTCOME_OFF_WAYWARD = 101


def parse_str_ts(timestamp: str) -> float:
    h, m, s = timestamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _parse_position(position: List[float], fidelity_version: int) -> Point:
    # location is cell based
    # [1, 120] x [1, 80]
    # +-----+------+
    # | 1,1 | 2, 1 |
    # +-----+------+
    # | 1,2 | 2,2  |
    # +-----+------+
    cell_side = 0.1 if fidelity_version == 2 else 1.0
    cell_relative_center = cell_side / 2
    return Point(
        x=position[0] - cell_relative_center,
        y=position[1] - cell_relative_center,
    )


def _parse_pass(
    pass_dict: Dict, current_team_map: Dict[int, int], fidelity_version: int
) -> Dict:
    if "outcome" in pass_dict:
        outcome_id = pass_dict["outcome"]["id"]
        if outcome_id == SB_PASS_OUTCOME_OUT:
            result = PassResult.OUT
        elif outcome_id == SB_PASS_OUTCOME_INCOMPLETE:
            result = PassResult.INCOMPLETE
        elif outcome_id == SB_PASS_OUTCOME_OFFSIDE:
            result = PassResult.OFFSIDE
        elif outcome_id == SB_PASS_OUTCOME_INJURY_CLEARANCE:
            result = PassResult.OUT
        elif outcome_id == SB_PASS_OUTCOME_UNKNOWN:
            result = None
        else:
            raise Exception(f"Unknown pass outcome: {outcome_id}")

        receiver_player_jersey_no = None
        receiver_position = None
    else:
        result = PassResult.COMPLETE
        receiver_player_jersey_no = current_team_map[
            pass_dict["recipient"]["id"]
        ]
        receiver_position = _parse_position(
            pass_dict["end_location"], fidelity_version
        )

    return dict(
        result=result,
        receiver_position=receiver_position,
        receiver_player_jersey_no=receiver_player_jersey_no,
    )


def _parse_shot(shot_dict: Dict) -> Dict:
    outcome_id = shot_dict["outcome"]["id"]
    if outcome_id == SB_SHOT_OUTCOME_OFF_TARGET:
        result = ShotResult.OFF_TARGET
    elif outcome_id == SB_SHOT_OUTCOME_SAVED:
        result = ShotResult.SAVED
    elif outcome_id == SB_SHOT_OUTCOME_POST:
        result = ShotResult.POST
    elif outcome_id == SB_SHOT_OUTCOME_OFF_WAYWARD:
        result = ShotResult.OFF_TARGET
    elif outcome_id == SB_SHOT_OUTCOME_BLOCKED:
        result = ShotResult.BLOCKED
    elif outcome_id == SB_SHOT_OUTCOME_GOAL:
        result = ShotResult.GOAL
    else:
        raise Exception(f"Unknown shot outcome: {outcome_id}")

    return dict(result=result)


def _parse_carry(carry_dict: Dict, fidelity_version: int) -> Dict:
    return dict(
        result=CarryResult.COMPLETE,
        end_position=_parse_position(
            carry_dict["end_location"], fidelity_version
        ),
    )


def _parse_take_on(take_on_dict: Dict) -> Dict:
    if "outcome" in take_on_dict:
        outcome_id = take_on_dict["outcome"]["id"]
        if outcome_id == SB_PASS_OUTCOME_OUT:
            result = TakeOnResult.OUT
        elif outcome_id == SB_PASS_OUTCOME_INCOMPLETE:
            result = TakeOnResult.INCOMPLETE
        elif outcome_id == SB_PASS_OUTCOME_COMPLETE:
            result = TakeOnResult.COMPLETE
        else:
            raise Exception(
                f"Unknown pass outcome: {take_on_dict['outcome']['name']}({outcome_id})"
            )
    else:
        result = TakeOnResult.COMPLETE

    return dict(result=result)


def _determine_xy_fidelity_versions(events: List[Dict]) -> Tuple[int, int]:
    """
    Find out if x and y are integers disguised as floats
    """
    shot_fidelity_version = 1
    xy_fidelity_version = 1
    for event in events:
        if "location" in event:
            x, y, *_ = event["location"]

            if not x.is_integer() or not y.is_integer():
                event_type = event["type"]["id"]
                if event_type == SB_EVENT_TYPE_SHOT:
                    shot_fidelity_version = 2
                elif event_type in (
                    SB_EVENT_TYPE_CARRY,
                    SB_EVENT_TYPE_DRIBBLE,
                    SB_EVENT_TYPE_PASS,
                ):
                    xy_fidelity_version = 2
    return shot_fidelity_version, xy_fidelity_version


class StatsBombSerializer(EventDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "event_data" not in inputs:
            raise ValueError("Please specify a value for input 'event_data'")
        if "lineup_data" not in inputs:
            raise ValueError("Please specify a value for input 'lineup_data'")

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> EventDataset:
        """
                Deserialize StatsBomb event data into a `EventDataset`.

                Parameters
                ----------
                inputs : dict
                    input `event_data` should point to a `Readable` object containing
                    the 'json' formatted event data. input `lineup_data` should point
                    to a `Readable` object containing the 'json' formatted lineup data.
                options : dict
                    Options for deserialization of the StatsBomb file. Possible options are
                    `event_types` (list of event types) to specify the event types that
                    should be returned. Valid types: "shot", "pass", "carry", "take_on" and
                    "generic". Generic is everything other than the first 4. Those events
                    are barely parsed. This type of event can be used to do the parsing
                    yourself.
                    Every event has a 'raw_event' attribute which contains the original
                    dictionary.
                Returns
                -------
                dataset : EventDataset
                Raises
                ------

                See Also
                --------

                Examples
                --------
                >>> serializer = StatsBombSerializer()
                >>> with open("events/12312312.json", "rb") as event_data, \
                >>>      open("lineups/123123123.json", "rb") as lineup_data:
                >>>
                >>>     dataset = serializer.deserialize(
                >>>         inputs={
                >>>             'event_data': event_data,
                >>>             'lineup_data': lineup_data
                >>>         },
                >>>         options={
                >>>             'event_types': ["pass", "take_on", "carry", "shot"]
                >>>         }
                >>>     )
                """
        self.__validate_inputs(inputs)
        if not options:
            options = {}

        with performance_logging("load data", logger=logger):
            raw_events = json.load(inputs["event_data"])
            home_lineup, away_lineup = json.load(inputs["lineup_data"])
            (
                shot_fidelity_version,
                xy_fidelity_version,
            ) = _determine_xy_fidelity_versions(raw_events)
            logger.info(
                f"Determined Fidelity versions: shot v{shot_fidelity_version} / XY v{xy_fidelity_version}"
            )

        with performance_logging("parse data", logger=logger):
            home_player_map = {
                player["player_id"]: str(player["jersey_number"])
                for player in home_lineup["lineup"]
            }
            away_player_map = {
                player["player_id"]: str(player["jersey_number"])
                for player in away_lineup["lineup"]
            }

            wanted_event_types = [
                EventType[event_type.upper()]
                for event_type in options.get("event_types", [])
            ]

            periods = []
            period = None
            events = []
            for raw_event in raw_events:
                if raw_event["team"]["id"] == home_lineup["team_id"]:
                    team = Team.HOME
                    current_team_map = home_player_map
                elif raw_event["team"]["id"] == away_lineup["team_id"]:
                    team = Team.AWAY
                    current_team_map = away_player_map
                else:
                    raise Exception(
                        f"Unknown team_id {raw_event['team']['id']}"
                    )

                if (
                    raw_event["possession_team"]["id"]
                    == home_lineup["team_id"]
                ):
                    possession_team = Team.HOME
                elif (
                    raw_event["possession_team"]["id"]
                    == away_lineup["team_id"]
                ):
                    possession_team = Team.AWAY
                else:
                    raise Exception(
                        f"Unknown possession_team_id: {raw_event['possession_team']}"
                    )

                timestamp = parse_str_ts(raw_event["timestamp"])
                period_id = int(raw_event["period"])
                if not period or period.id != period_id:
                    period = Period(
                        id=period_id,
                        start_timestamp=(
                            timestamp
                            if not period
                            # period = [start, end], add millisecond to prevent overlapping
                            else timestamp + period.end_timestamp + 0.001
                        ),
                        end_timestamp=None,
                    )
                    periods.append(period)
                else:
                    period.end_timestamp = period.start_timestamp + timestamp

                player_jersey_no = None
                if "player" in raw_event:
                    player_jersey_no = current_team_map[
                        raw_event["player"]["id"]
                    ]

                event_type = raw_event["type"]["id"]
                if event_type == SB_EVENT_TYPE_SHOT:
                    fidelity_version = shot_fidelity_version
                elif event_type in (
                    SB_EVENT_TYPE_CARRY,
                    SB_EVENT_TYPE_DRIBBLE,
                    SB_EVENT_TYPE_PASS,
                ):
                    fidelity_version = xy_fidelity_version
                else:
                    # TODO: Uh ohhhh.. don't know which one to pick
                    fidelity_version = xy_fidelity_version

                generic_event_kwargs = dict(
                    # from DataRecord
                    period=period,
                    timestamp=timestamp,
                    ball_owning_team=possession_team,
                    ball_state=BallState.ALIVE,
                    # from Event
                    event_id=raw_event["id"],
                    team=team,
                    player_jersey_no=player_jersey_no,
                    position=(
                        _parse_position(
                            raw_event.get("location"), fidelity_version
                        )
                        if "location" in raw_event
                        else None
                    ),
                    raw_event=raw_event,
                )

                if event_type == SB_EVENT_TYPE_PASS:
                    pass_event_kwargs = _parse_pass(
                        pass_dict=raw_event["pass"],
                        current_team_map=current_team_map,
                        fidelity_version=fidelity_version,
                    )

                    event = PassEvent(
                        # TODO: Consider moving this to _parse_pass
                        receive_timestamp=timestamp + raw_event["duration"],
                        **pass_event_kwargs,
                        **generic_event_kwargs,
                    )
                elif event_type == SB_EVENT_TYPE_SHOT:
                    shot_event_kwargs = _parse_shot(
                        shot_dict=raw_event["shot"]
                    )
                    event = ShotEvent(
                        **shot_event_kwargs, **generic_event_kwargs
                    )

                # For dribble and carry the definitions
                # are flipped between Statsbomb and kloppy
                elif event_type == SB_EVENT_TYPE_DRIBBLE:
                    take_on_event_kwargs = _parse_take_on(
                        take_on_dict=raw_event["dribble"]
                    )
                    event = TakeOnEvent(
                        **take_on_event_kwargs, **generic_event_kwargs
                    )
                elif event_type == SB_EVENT_TYPE_CARRY:
                    carry_event_kwargs = _parse_carry(
                        carry_dict=raw_event["carry"],
                        fidelity_version=fidelity_version,
                    )
                    event = CarryEvent(
                        # TODO: Consider moving this to _parse_carry
                        end_timestamp=timestamp + raw_event["duration"],
                        **carry_event_kwargs,
                        **generic_event_kwargs,
                    )
                else:
                    event = GenericEvent(result=None, **generic_event_kwargs)

                if (
                    not wanted_event_types
                    or event.event_type in wanted_event_types
                ):
                    events.append(event)

        return EventDataset(
            flags=DatasetFlag.BALL_OWNING_TEAM,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(0, 120), y_dim=Dimension(0, 80)
            ),
            periods=periods,
            records=events,
        )

    def serialize(self, data_set: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
