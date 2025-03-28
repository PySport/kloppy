[](){#kloppy.domain.EventType}

{{ render_provider_selectbox() }}

# Event Types

Each event in kloppy's data model is categorized by a specific type that defines
the general category to which the event belongs. By default, every event from the
data provider's original dataset is deserialized as a [`GenericEvent`][kloppy.domain.GenericEvent].
However, depending on the level of support implemented for each data provider,
some events are further converted into more specific event types. The following list
outlines all event types currently available in kloppy's data model and indicates
their availability for each data source. Additionally, each event type may include
specific attributes, which are detailed in the subsequent sections.

{{ render_event_types() }}
