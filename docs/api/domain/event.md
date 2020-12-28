## Dataset

::: kloppy.domain.models.event.EventDataset
    selection:
        inherited_members: true
        members:
            - "to_pandas"
            - "transform"
            - "filter"
            - "add_state"

## Events

### Event base class

::: kloppy.domain.models.event.Event

::: kloppy.domain.models.event.ShotEvent
::: kloppy.domain.models.event.PassEvent
::: kloppy.domain.models.event.TakeOnEvent
::: kloppy.domain.models.event.CarryEvent
::: kloppy.domain.models.event.RecoveryEvent

::: kloppy.domain.models.event.SubstitutionEvent
::: kloppy.domain.models.event.PlayerOnEvent
::: kloppy.domain.models.event.PlayerOffEvent

::: kloppy.domain.models.event.CardEvent
::: kloppy.domain.models.event.FoulCommittedEvent

::: kloppy.domain.models.event.BallOutEvent

::: kloppy.domain.models.event.GenericEvent


## Results

::: kloppy.domain.models.event.ShotResult
::: kloppy.domain.models.event.PassResult
::: kloppy.domain.models.event.CarryResult
::: kloppy.domain.models.event.TakeOnResult


## Types

::: kloppy.domain.models.event.EventType
::: kloppy.domain.models.event.CardType


## Qualifiers

Qualifier specify additional information about certain events. See [`get_qualifier_value`](kloppy.domain.models.event.Event.get_qualifier_value) for usage.

::: kloppy.domain.models.event.Qualifier

::: kloppy.domain.models.event.SetPieceQualifier
::: kloppy.domain.models.event.SetPieceType

::: kloppy.domain.models.event.BodyPartQualifier
::: kloppy.domain.models.event.BodyPart

::: kloppy.domain.models.event.PassQualifier
::: kloppy.domain.models.event.PassType
        




