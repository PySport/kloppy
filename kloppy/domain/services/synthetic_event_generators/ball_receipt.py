from typing import Optional

from kloppy.domain import (
    EventDataset,
    EventType,
    EventFactory,
    PassResult,
    PassEvent,
    CarryEvent,
    RecoveryEvent,
    ClearanceEvent,
    TakeOnEvent,
    ShotEvent,
    InterceptionEvent,
    BallReceiptResult,
    MiscontrolEvent,
    FoulCommittedEvent,
)
from kloppy.domain.services.synthetic_event_generators.synthetic_event_generator import (
    SyntheticEventGenerator,
)

POSSESSING_ON_BALL = (
    PassEvent,
    ShotEvent,
    TakeOnEvent,
    CarryEvent,
    RecoveryEvent,
    ClearanceEvent,
    InterceptionEvent,
    RecoveryEvent,
)


class SyntheticBallReceiptGenerator(SyntheticEventGenerator):
    def __init__(self, event_factory: Optional[EventFactory] = None, **kwargs):
        self.event_factory = event_factory or EventFactory()

    def add_synthetic_event(self, dataset: EventDataset) -> EventDataset:

        for idx, event in enumerate(dataset.events):
            if (
                event.event_type == EventType.PASS
                and event.result == PassResult.COMPLETE
            ):
                idx_plus = 1
                result = None
                while idx + idx_plus < len(dataset.events):
                    next_event = dataset.events[idx + idx_plus]

                    if isinstance(next_event, POSSESSING_ON_BALL):
                        result = (
                            BallReceiptResult.COMPLETE
                            if event.team.team_id == next_event.team.team_id
                            else BallReceiptResult.INCOMPLETE
                        )
                        break
                    elif isinstance(next_event, MiscontrolEvent):
                        result = BallReceiptResult.INCOMPLETE
                        break
                    elif isinstance(next_event, FoulCommittedEvent):
                        result = (
                            BallReceiptResult.INCOMPLETE
                            if event.team.team_id == next_event.team.team_id
                            else BallReceiptResult.COMPLETE
                        )
                        break

                    idx_plus += 1

                if result is not None:
                    generic_event_args = {
                        "event_id": f"ball_receipt-{event.event_id}",
                        "coordinates": event.receiver_coordinates,
                        "team": event.team,
                        "player": event.receiver_player,
                        "ball_owning_team": event.ball_owning_team,
                        "ball_state": event.ball_state,
                        "period": event.period,
                        "timestamp": event.receive_timestamp,
                        "raw_event": None,
                    }
                    ball_receipt_event_args = {
                        "qualifiers": None,
                        "result": result,
                    }
                    new_ball_receipt = self.event_factory.build_ball_receipt(
                        **ball_receipt_event_args,
                        **generic_event_args,
                    )
                    dataset.records.insert(idx + 1, new_ball_receipt)

        return dataset
