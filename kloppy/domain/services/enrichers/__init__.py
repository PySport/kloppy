from dataclasses import dataclass

from ...models.tracking import Dataset as TrackingDataset
from ...models.event import Dataset as EventDataset
from ...models.common import DatasetFlag, Team, BallState


class TrackingPossessionEnricher:
    def enrich_inplace(
        self, tracking_dataset: TrackingDataset, event_dataset: EventDataset
    ) -> None:
        """
            Return an enriched tracking data set.

            Use the event data to rebuild game state.

            Iterate through all tracking data events and apply event data to the GameState whenever
            they happen.

        """
        if tracking_dataset.flags & (
            DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE
        ):
            return

        if not event_dataset.flags & (
            DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE
        ):
            raise Exception(
                "Event Dataset does not contain ball owning team or ball state information"
            )

        # set some defaults
        next_event_idx = 0
        current_ball_owning_team = None
        current_ball_state = None

        for frame in tracking_dataset.records:
            if next_event_idx < len(event_dataset.records):
                event = event_dataset.records[next_event_idx]
                if (
                    frame.period.id == event.period.id
                    and frame.timestamp >= event.timestamp
                ):
                    current_ball_owning_team = event.ball_owning_team
                    current_ball_state = event.ball_state
                    next_event_idx += 1

            frame.ball_owning_team = current_ball_owning_team
            frame.ball_state = current_ball_state
