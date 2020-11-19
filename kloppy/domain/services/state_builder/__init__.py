from dataclasses import replace

from kloppy.domain import List, EventDataset

# register all of them
from . import builders

from .registered import create_state_builder


def add_state(dataset: EventDataset, *builder_keys: List[str]) -> EventDataset:
    if len(builder_keys) == 1 and isinstance(builder_keys[0], list):
        builder_keys = builder_keys[0]

    builders = {
        builder_key: create_state_builder(builder_key)
        for builder_key in builder_keys
    }

    state = {
        builder_key: builder.initial_state(dataset)
        for builder_key, builder in builders.items()
    }

    events = []
    for event in dataset.events:

        state = {
            builder_key: builder.reduce_before(state[builder_key], event)
            for builder_key, builder in builders.items()
        }

        events.append(replace(event, state=state))

        state = {
            builder_key: builder.reduce_after(state[builder_key], event)
            for builder_key, builder in builders.items()
        }

    return replace(dataset, records=events)
