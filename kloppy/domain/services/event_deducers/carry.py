import bisect
from datetime import timedelta
from typing import List

import pandas as pd

from kloppy.domain import (
    EventDataset,
    Event,
    EventType,
    BodyPart,
    CarryResult,
    CarryEvent,
    GenericEvent,
    EventFactory,
    Unit,
)
from kloppy.domain.services.event_deducers.event_deducer import (
    EventDatasetDeduducer,
)


class CarryDeducer(EventDatasetDeduducer):
    def deduce(self, dataset: EventDataset):
        event_factory = EventFactory()

        # TODO: config
        min_dribble_length = 3
        max_dribble_length = 60
        max_dribble_duration = timedelta(seconds=10)

        unit = Unit("m")
        min_dribble_length = unit.convert(
            dataset.metadata.coordinate_system.pitch_dimensions.unit,
            min_dribble_length,
        )
        max_dribble_length = unit.convert(
            dataset.metadata.coordinate_system.pitch_dimensions.unit,
            max_dribble_length,
        )

        new_carries = []
        for idx, event in enumerate(dataset.events):
            if isinstance(event, GenericEvent):
                continue
            if event.event_type in [
                EventType.FOUL_COMMITTED,
                EventType.CARD,
                EventType.SUBSTITUTION,
                EventType.FORMATION_CHANGE,
                EventType.CLEARANCE,
            ]:
                continue
            idx_sum = 1
            generic_next_event = True
            while idx + idx_sum < len(dataset.events) and generic_next_event:
                next_event = dataset.events[idx + idx_sum]

                if isinstance(next_event, GenericEvent):
                    idx += 1
                    continue
                else:
                    generic_next_event = False
                if not event.team.team_id == next_event.team.team_id:
                    continue

                if next_event.event_type in [
                    EventType.FOUL_COMMITTED,
                    EventType.CARD,
                    EventType.SUBSTITUTION,
                    EventType.FORMATION_CHANGE,
                ]:
                    continue
                # not headed shot
                if (
                    (hasattr(next_event, "body_part"))
                    and (next_event.event_type == EventType.SHOT)
                    and (
                        next_event.body_part.type.isin(
                            [BodyPart.HEAD, BodyPart.HEAD_OTHER]
                        )
                    )
                ):
                    continue

                if hasattr(event, "end_coordinates"):
                    last_coord = event.end_coordinates
                elif hasattr(event, "receiver_coordinates"):
                    last_coord = event.receiver_coordinates
                else:
                    last_coord = event.coordinates

                new_coord = next_event.coordinates

                # Not far enough
                if new_coord.distance_to(last_coord) < min_dribble_length:
                    continue
                # Too far
                if new_coord.distance_to(last_coord) > max_dribble_length:
                    continue

                dt = next_event.timestamp - event.timestamp
                # not same phase
                if dt > max_dribble_duration:
                    continue
                # not same period
                if not event.period.id == next_event.period.id:
                    continue

                if hasattr(event, "end_timestamp"):
                    last_timestamp = event.end_timestamp
                else:
                    last_timestamp = (
                        event.timestamp
                        + (next_event.timestamp - event.timestamp) / 10
                    )

                generic_event_args = {
                    "event_id": 1,  # TODO: generate event id
                    "coordinates": last_coord,
                    "team": next_event.team,
                    "player": next_event.player,
                    "ball_owning_team": next_event.ball_owning_team,
                    "ball_state": event.ball_state,
                    "period": next_event.period,
                    "timestamp": last_timestamp,
                    "raw_event": {},
                }
                carry_event_args = {
                    "result": CarryResult.COMPLETE,
                    "qualifiers": None,
                    "end_coordinates": new_coord,
                    "end_timestamp": next_event.timestamp,
                }
                new_carry = event_factory.build_carry(
                    **carry_event_args, **generic_event_args
                )
                new_carries.append(new_carry)

        for new_carry in new_carries:
            pos = bisect.bisect_left(
                [e.time for e in dataset.events], new_carry.time
            )
            dataset.records.insert(pos, new_carry)
        print(f"total carries: {len(new_carries)}/{len(dataset.events)}")
