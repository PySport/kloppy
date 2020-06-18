from typing import Tuple, Dict, List
import logging
from datetime import datetime
from lxml import objectify

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


def _parse_f24_datetime(dt_str: str) -> float:
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f").timestamp()


def _parse_pass(qualifiers: Dict[int, str], outcome: int) -> Dict:
    if outcome:
        receiver_position = Point(
            x=float(qualifiers[140]), y=float(qualifiers[141])
        )
        result = PassResult.COMPLETE
    else:
        result = PassResult.INCOMPLETE
        receiver_position = None

    return dict(
        result=result,
        receiver_position=receiver_position,
        receiver_player_jersey_no=None,
        receive_timestamp=None,
    )


def _parse_offside_pass() -> Dict:
    return dict(
        result=PassResult.OFFSIDE,
        receiver_position=None,
        receiver_player_jersey_no=None,
        receive_timestamp=None,
    )


def _parse_take_on(outcome: int) -> Dict:
    if outcome:
        result = TakeOnResult.COMPLETE
    else:
        result = TakeOnResult.INCOMPLETE
    return dict(result=result)


def _parse_shot(
    qualifiers: Dict[int, str], type_id: int, position: Point
) -> Dict:
    if type_id == EVENT_TYPE_SHOT_GOAL:
        if 28 in qualifiers:
            position = Point(x=100 - position.x, y=100 - position.y)
        result = ShotResult.GOAL
    else:
        result = None

    return dict(position=position, result=result)


EVENT_TYPE_START_PERIOD = 32
EVENT_TYPE_END_PERIOD = 30

EVENT_TYPE_PASS = 1
EVENT_TYPE_OFFSIDE_PASS = 1
EVENT_TYPE_TAKE_ON = 3
EVENT_TYPE_SHOT_MISS = 13
EVENT_TYPE_SHOT_POST = 14
EVENT_TYPE_SHOT_SAVED = 15
EVENT_TYPE_SHOT_GOAL = 16


class OptaSerializer(EventDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "f7_data" not in inputs:
            raise ValueError("Please specify a value for input 'f7_data'")
        if "f24_data" not in inputs:
            raise ValueError("Please specify a value for input 'f24_data'")

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> EventDataset:
        """
                Deserialize Opta event data into a `EventDataset`.

                Parameters
                ----------
                inputs : dict
                    input `f24_data` should point to a `Readable` object containing
                    the 'xml' formatted event data. input `f7_data` should point
                    to a `Readable` object containing the 'xml' formatted f7 data.
                options : dict
                    Options for deserialization of the Opta file. Possible options are
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
                >>> serializer = OptaSerializer()
                >>> with open("123_f24.xml", "rb") as f24_data, \
                >>>      open("123_f7.xml", "rb") as f7_data:
                >>>
                >>>     dataset = serializer.deserialize(
                >>>         inputs={
                >>>             'f24_data': f24_data,
                >>>             'f7_data': f7_data
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
            f7_root = objectify.fromstring(inputs["f7_data"].read())
            f24_root = objectify.fromstring(inputs["f24_data"].read())

            wanted_event_types = [
                EventType[event_type.upper()]
                for event_type in options.get("event_types", [])
            ]

        with performance_logging("parse data", logger=logger):
            matchdata_path = objectify.ObjectPath(
                "SoccerFeed.SoccerDocument.MatchData"
            )
            team_elms = list(
                matchdata_path.find(f7_root).iterchildren("TeamData")
            )

            away_player_map = {}
            home_player_map = {}
            home_team_id = None
            away_team_id = None
            for team_elm in team_elms:
                player_map = {
                    player_elm.attrib["PlayerRef"].lstrip(
                        "p"
                    ): player_elm.attrib["ShirtNumber"]
                    for player_elm in team_elm.find(
                        "PlayerLineUp"
                    ).iterchildren("MatchPlayer")
                }
                team_id = team_elm.attrib["TeamRef"].lstrip("t")

                if team_elm.attrib["Side"] == "Home":
                    home_player_map = player_map
                    home_team_id = team_id
                elif team_elm.attrib["Side"] == "Away":
                    away_player_map = player_map
                    away_team_id = team_id
                else:
                    raise Exception(f"Unknown side: {team_elm.attrib['Side']}")

            if not away_player_map or not home_player_map:
                raise Exception("LineUp incomplete")

            game_elm = f24_root.find("Game")
            periods = [
                Period(id=1, start_timestamp=None, end_timestamp=None,),
                Period(id=2, start_timestamp=None, end_timestamp=None,),
            ]
            events = []
            for event_elm in game_elm.iterchildren("Event"):
                event_id = event_elm.attrib["id"]
                type_id = int(event_elm.attrib["type_id"])
                timestamp = _parse_f24_datetime(event_elm.attrib["timestamp"])
                period_id = int(event_elm.attrib["period_id"])
                for period in periods:
                    if period.id == period_id:
                        break
                else:
                    logger.debug(
                        f"Skipping event {event_id} because period doesn't match {period_id}"
                    )
                    continue

                if type_id == EVENT_TYPE_START_PERIOD:
                    logger.debug(
                        f"Set start of period {period.id} to {timestamp}"
                    )
                    period.start_timestamp = timestamp
                elif type_id == EVENT_TYPE_END_PERIOD:
                    logger.debug(
                        f"Set end of period {period.id} to {timestamp}"
                    )
                    period.end_timestamp = timestamp
                else:
                    if not period.start_timestamp:
                        # not started yet
                        continue

                    if event_elm.attrib["team_id"] == home_team_id:
                        team = Team.HOME
                        current_team_map = home_player_map
                    elif event_elm.attrib["team_id"] == away_team_id:
                        team = Team.AWAY
                        current_team_map = away_player_map
                    else:
                        raise Exception(
                            f"Unknown team_id {event_elm.attrib['team_id']}"
                        )

                    x = float(event_elm.attrib["x"])
                    y = float(event_elm.attrib["y"])
                    outcome = int(event_elm.attrib["outcome"])
                    qualifiers = {
                        int(
                            qualifier_elm.attrib["qualifier_id"]
                        ): qualifier_elm.attrib.get("value")
                        for qualifier_elm in event_elm.iterchildren("Q")
                    }
                    player_jersey_no = None
                    if "player_id" in event_elm.attrib:
                        player_jersey_no = current_team_map[
                            event_elm.attrib["player_id"]
                        ]

                    generic_event_kwargs = dict(
                        # from DataRecord
                        period=period,
                        timestamp=timestamp - period.start_timestamp,
                        ball_owning_team=None,
                        ball_state=BallState.ALIVE,
                        # from Event
                        event_id=event_id,
                        team=team,
                        player_jersey_no=player_jersey_no,
                        position=Point(x=x, y=y),
                        raw_event=event_elm,
                    )

                    if type_id == EVENT_TYPE_PASS:
                        pass_event_kwargs = _parse_pass(qualifiers, outcome)
                        event = PassEvent(
                            **pass_event_kwargs, **generic_event_kwargs,
                        )
                    elif type_id == EVENT_TYPE_OFFSIDE_PASS:
                        pass_event_kwargs = _parse_offside_pass()
                        event = PassEvent(
                            **pass_event_kwargs, **generic_event_kwargs,
                        )
                    elif type_id == EVENT_TYPE_TAKE_ON:
                        take_on_event_kwargs = _parse_take_on(outcome)
                        event = TakeOnEvent(
                            **take_on_event_kwargs, **generic_event_kwargs,
                        )
                    elif type_id in (
                        EVENT_TYPE_SHOT_MISS,
                        EVENT_TYPE_SHOT_POST,
                        EVENT_TYPE_SHOT_SAVED,
                        EVENT_TYPE_SHOT_GOAL,
                    ):
                        shot_event_kwargs = _parse_shot(
                            qualifiers,
                            type_id,
                            position=generic_event_kwargs["position"],
                        )
                        kwargs = {}
                        kwargs.update(generic_event_kwargs)
                        kwargs.update(shot_event_kwargs)
                        event = ShotEvent(**kwargs)
                    else:
                        event = GenericEvent(
                            **generic_event_kwargs, result=None
                        )

                    if (
                        not wanted_event_types
                        or event.event_type in wanted_event_types
                    ):
                        events.append(event)

        return EventDataset(
            flags=DatasetFlag.BALL_OWNING_TEAM,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(0, 100), y_dim=Dimension(0, 100)
            ),
            periods=periods,
            records=events,
        )

    def serialize(self, data_set: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
