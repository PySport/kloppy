from typing import Tuple
import csv

from kloppy.domain import (
    EventDataSet, Team, Point, Period, Orientation,
    DataSetFlag, PitchDimensions, Dimension,
    AttackingDirection
)
from kloppy.domain.models.event import (
    EventType,
    SetPieceEvent, PassEvent, RecoveryEvent,
    BallOutEvent, BallLossEvent,
    ShotEvent, FaultReceivedEvent, ChallengeEvent,
    CardEvent
)
from kloppy.infra.utils import Readable

from .. import EventDataSerializer

from .subtypes import *

event_type_map: Dict[str, EventType] = {
    "SET PIECE": EventType.SET_PIECE,
    "RECOVERY": EventType.RECOVERY,
    "PASS": EventType.PASS,
    "BALL LOST": EventType.BALL_LOST,
    "BALL OUT": EventType.BALL_OUT,
    "SHOT": EventType.SHOT,
    "FAULT RECEIVED": EventType.FAULT_RECEIVED,
    "CHALLENGE": EventType.CHALLENGE,
    "CARD": EventType.CARD
}

# https://github.com/Friends-of-Tracking-Data-FoTD/passing-networks-in-python/blob/master/processing/tracking.py
# https://github.com/HarvardSoccer/TrackingData/blob/fa7701893c928e9fcec358ec6e281743c00e6bc1/Metrica.py#L251


class MetricaEventSerializer(EventDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for input 'raw_data'")

    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> EventDataSet:
        self.__validate_inputs(inputs)

        periods = []
        period = None

        events = []

        reader = csv.DictReader(map(lambda x: x.decode('utf-8'), inputs['raw_data']))
        for event_id, record in enumerate(reader):
            event_type = event_type_map[record['Type']]
            subtypes = record['Subtype'].split('-')

            start_timestamp = float(record['Start Time [s]'])
            end_timestamp = float(record['End Time [s]'])

            period_id = int(record['Period'])
            if not period or period.id != period_id:
                period = Period(
                    id=period_id,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp
                )
                periods.append(period)
            else:
                period.end_timestamp = end_timestamp

            if record['Team'] == 'Home':
                team = Team.HOME
            elif record['Team'] == 'Away':
                team = Team.AWAY
            else:
                raise ValueError(f'Unknown team: {record["team"]}')

            event_kwargs = dict(
                # From DataRecord:
                timestamp=start_timestamp,
                ball_owning_team=None,  ## todo
                ball_state=None,  # todo
                period=period,

                # From Event:
                event_id=event_id,
                team=team,
                end_timestamp=end_timestamp,
                player_jersey_no=record['From'][6:],
                position=Point(
                    x=float(record['Start X']),
                    y=1 - float(record['Start Y'])
                ) if record['Start X'] != 'NaN' else None,
            )

            secondary_position = None
            if record['End X'] != 'NaN':
                secondary_position = Point(
                    x=float(record['End X']),
                    y=1 - float(record['End Y'])
                )

            secondary_jersey_no = None
            if record['To']:
                secondary_jersey_no = record['To'][6:]

            event = None
            if event_type == EventType.SET_PIECE:
                set_piece, fk_attempt, retaken = \
                    build_subtypes(subtypes, [SetPiece, FKAttempt, Retaken])

                event = SetPieceEvent(
                    **event_kwargs
                )
            elif event_type == EventType.RECOVERY:
                interference1, interference2 = \
                    build_subtypes(subtypes, [Interference1, Interference2])

                event = RecoveryEvent(
                    **event_kwargs
                )
            elif event_type == EventType.PASS:
                body_part, attempt, deflection, offside = \
                    build_subtypes(subtypes, [BodyPart, Attempt, Deflection, Offside])

                event = PassEvent(
                    receiver_position=secondary_position,
                    receiver_player_jersey_no=secondary_jersey_no,
                    **event_kwargs
                )
            elif event_type == EventType.BALL_LOST:
                body_part, attempt, interference1, intervention, deflection, offside = \
                    build_subtypes(subtypes, [
                        BodyPart, Attempt, Interference1, Intervention,
                        Deflection, Offside
                    ])

                event = BallLossEvent(
                    **event_kwargs
                )
            elif event_type == EventType.BALL_OUT:
                body_part, attempt, intervention, deflection, offside, own_goal = \
                    build_subtypes(subtypes, [
                        BodyPart, Attempt, Intervention, Deflection,
                        Offside, OwnGoal
                    ])

                event = BallOutEvent(
                    **event_kwargs
                )
            elif event_type == EventType.SHOT:
                body_part, deflection, shot_direction, shot_result, offside = \
                    build_subtypes(subtypes, [
                        BodyPart, Deflection, ShotDirection,
                        ShotResult, Offside
                    ])

                event = ShotEvent(
                    shot_result=shot_result,
                    **event_kwargs
                )
            elif event_type == EventType.FAULT_RECEIVED:
                event = FaultReceivedEvent(
                    **event_kwargs
                )
            elif event_type == EventType.CHALLENGE:
                challenge, fault, challenge_result = \
                    build_subtypes(subtypes, [Challenge, Fault, ChallengeResult])

                event = ChallengeEvent(
                    **event_kwargs
                )
            elif event_type == EventType.CARD:
                card, = build_subtypes(subtypes, [Card])

                event = CardEvent(
                    **event_kwargs
                )
            else:
                raise NotImplementedError(f"EventType {event_type} not implemented")

            events.append(event)

        orientation = (
            Orientation.FIXED_HOME_AWAY
            if periods[0].attacking_direction == AttackingDirection.HOME_AWAY else
            Orientation.FIXED_AWAY_HOME
        )

        return EventDataSet(
            flags=DataSetFlag.BALL_STATE | DataSetFlag.BALL_OWNING_TEAM,
            orientation=orientation,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(0, 1),
                y_dim=Dimension(0, 1)
            ),
            periods=periods,
            records=events
        )

    def serialize(self, data_set: EventDataSet) -> Tuple[str, str]:
        raise NotImplementedError
