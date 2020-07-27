from typing import List

from kloppy.domain import Score, EventDataset, Event, ShotEvent, ShotResult, State, Window
from kloppy.domain.models.event import SubstitutionEvent

#
#
# class Comparable(metaclass=ABCMeta):
#     @abstractmethod
#     def __gt__(self, other: Any) -> bool: pass
#     ... # __lt__ etc. as well
# # state_view_fn: Callable[[State], Comparable]


class Windower:
    def _reduce_state(self, current_state: State, event: Event):
        new_state = None
        if isinstance(event, SubstitutionEvent):
            new_state = current_state\
                .remove_player(event.player)\
                .add_player(event.replacement_player)
        elif isinstance(event, ShotEvent):
            if event.result == ShotResult.GOAL:
                new_state = current_state.add_goal(event.team)

        if not new_state:
            return False, current_state
        else:
            return True, new_state

    def create_windows(self, dataset: EventDataset) -> List[Window]:
        windows = []

        current_state = State(
            score=Score(home=0, away=0),
            players=set(dataset.metadata.teams[0].players) | set(dataset.metadata.teams[1].players)
        )

        current_window = Window(
            state=current_state,
            events=[]
        )
        windows.append(current_window)

        for event in dataset.events:
            current_window.events.append(event)

            state_changed, new_state = self._reduce_state(
                current_state,
                event
            )
            if state_changed:
                current_window = Window(
                    state=new_state,
                    events=[]
                )
                windows.append(current_window)
                current_state = new_state

        return windows
