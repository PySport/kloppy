# from dataclasses import dataclass
#
# from ...models.tracking import DataSet as TrackingDataSet, BallState, BallOwningTeam, DataSetFlag
# from ...models.event import DataSet as EventDataSet
#
#
# @dataclass
# class GameState(object):
#     ball_state: BallState
#     ball_owning_team: BallOwningTeam
#
#
# class TrackingPossessionEnricher(object):
#     def _reduce_game_state(self, game_state: GameState, Event: event) -> GameState:
#         pass
#
#     def enrich_inplace(self, tracking_data_set: TrackingDataSet, event_data_set: EventDataSet) -> None:
#         """
#             Return an enriched tracking data set.
#
#             Use the event data to rebuild game state.
#
#             Iterate through all tracking data events and apply event data to the GameState whenever
#             they happen.
#
#         """
#         if tracking_data_set.flags & (DataSetFlag.BALL_OWNING_TEAM | DataSetFlag.BALL_STATE):
#             return
#
#         # set some defaults
#         game_state = GameState(
#             ball_state=BallState.DEAD,
#             ball_owning_team=BallOwningTeam.HOME
#         )
#
#         next_event_idx = 0
#
#         for frame in tracking_data_set.frames:
#             if next_event_idx < len(event_data_set.frames):
#                 event = event_data_set.events[next_event_idx]
#                 if frame.period.id == event.period.id and frame.timestamp >= event.timestamp:
#                     game_state = self._reduce_game_state(
#                         game_state,
#                         event_data_set.events[next_event_idx]
#                     )
#                     next_event_idx += 1
#
#             frame.ball_owning_team = game_state.ball_owning_team
#             frame.ball_state = game_state.ball_state
