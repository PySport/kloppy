# Event Data Model

This section outlines the current state of kloppy's event data model. Each [`Event`][kloppy.domain.Event] consists of general attributes as well as event-specific attributes. The general attributes listed below are recorded for all event types, based on their applicability. Additional attributes are recorded depending on the specific [`EventType`][kloppy.domain.EventType] and each event can have a list of [`Qualifier`][kloppy.domain.Qualifier] entities providing additional information about the event.


!!! warning

    The implementation of the data model is not yet complete for all providers and some providers might simply
    not support certain parts of the data model (e.g., not all providers annotate the intended recipient of
    a pass). For each event type and qualifier, we provide a detailed overview describing if and how it is
    implemented for each data provider.

    The status of the implementation is indicated by the following icons:

      - :material-check: the implementation is complete
      - :material-close: not supported by the data provider
      - :material-progress-helper: not yet implemented
      - :material-progress-question: the status is unclear

## Event

{{ render_event_type("kloppy.domain.Event", show_providers=False) }}
