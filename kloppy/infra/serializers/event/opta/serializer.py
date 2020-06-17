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


EVENT_TYPE_START_PERIOD = 32
EVENT_TYPE_END_PERIOD = 30

EVENT_TYPE_PASS = 1
EVENT_TYPE_TAKE_ON = 3


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

        with performance_logging("parse data", logger=logger):
            matchdata_path = objectify.ObjectPath(
                "SoccerFeed.SoccerDocument.MatchData"
            )
            team_elms = list(
                matchdata_path.find(f7_root).iterchildren("TeamData")
            )

            away_player_map = {}
            home_player_map = {}
            for team_elm in team_elms:
                player_map = {
                    player_elm.attrib["PlayerRef"]: player_elm.attrib[
                        "ShirtNumber"
                    ]
                    for player_elm in team_elm.find(
                        "PlayerLineUp"
                    ).iterchildren("MatchPlayer")
                }

                if team_elm.attrib["Side"] == "Home":
                    home_player_map = player_map
                elif team_elm.attrib["Side"] == "Away":
                    away_player_map = player_map
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
                type_id = int(event_elm.attrib["type_id"])
                timestamp = _parse_f24_datetime(event_elm.attrib["timestamp"])
                period_id = int(event_elm.attrib["period_id"])
                for period in periods:
                    if period.id == period_id:
                        break
                else:
                    continue

                if type_id == EVENT_TYPE_START_PERIOD:
                    period.start_timestamp = timestamp
                elif type_id == EVENT_TYPE_END_PERIOD:
                    period.end_timestamp = timestamp
                elif type_id == EVENT_TYPE_PASS:
                    pass
                elif type_id == EVENT_TYPE_TAKE_ON:
                    pass

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
