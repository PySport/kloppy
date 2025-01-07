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
    def deduce_old(self, dataset: EventDataset) -> List[Event]:
        # TODO: config
        min_dribble_length = 2
        max_dribble_length = 50
        max_dribble_duration = timedelta(seconds=5)

        events = dataset.to_df()
        next_actions = events.shift(-1, fill_value=None)

        same_team = events.team_id == next_actions.team_id
        not_offensive_foul = same_team & (
            next_actions.event_type != EventType.FOUL_COMMITTED
        )

        not_headed_shot = (next_actions.event_type != EventType.SHOT) & (
            ~next_actions.body_part_type.isin(
                [BodyPart.HEAD, BodyPart.HEAD_OTHER]
            )
        )

        dx = events.end_coordinates_x - next_actions.coordinates_x
        dy = events.end_coordinates_y - next_actions.coordinates_y
        far_enough = dx**2 + dy**2 >= min_dribble_length**2
        not_too_far = dx**2 + dy**2 <= max_dribble_length**2

        dt = next_actions.timestamp - events.timestamp
        same_phase = dt < max_dribble_duration
        same_period = events.period_id == next_actions.period_id

        dribble_idx = (
            same_team
            & far_enough
            & not_too_far
            & same_phase
            & same_period
            & not_offensive_foul
            & not_headed_shot
        )

        dribbles = pd.DataFrame()
        prev = events[dribble_idx]
        nex = next_actions[dribble_idx]
        dribbles["period_id"] = nex.period_id
        dribbles["event_id"] = prev.event_id + 0.1
        dribbles["timestamp"] = (prev.timestamp + nex.timestamp) / 2
        if "timestamp" in events.columns:
            dribbles["timestamp"] = nex.timestamp
        dribbles["team_id"] = nex.team_id
        dribbles["player_id"] = nex.player_id
        dribbles["coordinates_x"] = prev.end_coordinates_x
        dribbles["coordinates_y"] = prev.end_coordinates_y
        dribbles["end_coordinates_x"] = nex.coordinates_x
        dribbles["end_coordinates_y"] = nex.coordinates_y
        dribbles["body_part_type"] = BodyPart.RIGHT_FOOT  # TODO: fix
        dribbles["event_type"] = EventType.CARRY
        dribbles["result"] = CarryResult.COMPLETE

        new_carries: List[Event] = []

        # Iterate over the rows of the dribbles DataFrame and create new Event objects
        for _, row in dribbles.iterrows():
            new_event = CarryEvent(
                event_id=row["event_id"],
                timestamp=row["timestamp"],
                team_id=row["team_id"],
                player_id=row["player_id"],
                coordinates_x=row["coordinates_x"],
                coordinates_y=row["coordinates_y"],
                end_coordinates_x=row["end_coordinates_x"],
                end_coordinates_y=row["end_coordinates_y"],
                body_part_type=row["body_part_type"],
                event_type=row["event_type"],
                result=row["result"],
            )
            # Append the new Event to the new_carries list
            new_carries.append(new_event)

        return events.values.tolist()

    def deduce(self, dataset: EventDataset):
        event_factory = EventFactory()
        # TODO: config
        min_dribble_length = 3
        max_dribble_length = 60
        unit = Unit("m")
        min_dribble_length = unit.convert(
            dataset.metadata.coordinate_system.pitch_dimensions.unit,
            min_dribble_length,
        )
        max_dribble_length = unit.convert(
            dataset.metadata.coordinate_system.pitch_dimensions.unit,
            max_dribble_length,
        )

        max_dribble_duration = timedelta(seconds=10)
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
                    # Handle the case where the attribute doesn't exist
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
