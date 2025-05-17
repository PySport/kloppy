# Event Data Model

This section outlines the current state of kloppy's event data model. Each [`Event`][kloppy.domain.Event] is associated with an [`EventType`][kloppy.domain.EventType] which classifies the general event type that has occurred. Furthermore, each [`Event`][kloppy.domain.Event] consists of general attributes as well as event type-specific attributes. The general attributes are recorded for all event types, based on their applicability. Additional attributes are recorded depending on the specific [`EventType`][kloppy.domain.EventType]. Each event can also have a list of [`Qualifier`][kloppy.domain.Qualifier] entities providing additional information about the event.

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

    Please [open a ticket](https://github.com/PySport/kloppy/issues) when you like to implement additional features.

