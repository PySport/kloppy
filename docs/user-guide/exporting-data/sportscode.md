# Exporting to SportsCode XML
Kloppy provides support for exporting event datasets to XML compatible with Hudl Sportscode. This functionality enables you to:

- Import events from all supported data providers in a Sportscode timeline
- Annotate matches with data-driven labels and tags.
- Enhance video analysis by combining tracking/event data with visual context.

## Converting to Sportcode

To export data into a format compatible with Sportscode, you first need to create a [`CodeDataset`][kloppy.domain.CodeDataset]. This is a collection of "codes", which is Sportscode’s basic unit for marking moments in a match, each with a start and end time, labels (like player and team), and other metadata.

The recommended workflow starts by filtering your raw event data to the specific actions you want to turn into codes (for example, shots, passes, or defensive actions).
Once filtered, you can use the [`from_dataset`][kloppy.domain.CodeDataset.from_dataset] method to map each event into a [`Code`][kloppy.domain.Code] object.

Below is a full example showing how to extract all shots from a StatsBomb dataset and prepare them as Sportscode codes:

```python
from kloppy import statsbomb
from kloppy.domain import Code, CodeDataset, EventType

dataset_shots = (
    statsbomb.load_open_data()
    .filter(
        lambda event: event.event_type == EventType.SHOT
    )
)

code_dataset = (
    CodeDataset
    .from_dataset(
        dataset_shots,
        lambda event: Code(
            code_id=None,  # make it auto increment on write
            code=event.event_name,
            period=event.period,
            timestamp=max(0, event.timestamp - 7),
            end_timestamp=event.timestamp + 5,
            labels={
                'Player': str(event.player),
                'Team': str(event.team)
            },

            # In the future next two won't be needed anymore
            ball_owning_team=None,
            ball_state=None
        )
    )
)
```

In this example:

- `code` is based on the event name (e.g., "Shot").
- `timestamp` and `end_timestamp` define the time window around the shot.
- `labels` attach important context to each code, making analysis easier in Sportscode.

## Saving to Sportscode format

Once you have created a [`CodeDataset`][kloppy.domain.CodeDataset], you can easily export it into a format compatible with Sportscode by using the [`sportscode.save()`][kloppy.sportscode.save] function from Kloppy.

Here’s a simple example:

```python
from kloppy import sportscode

# Assuming 'code_dataset' is your CodeDataset object
sportscode.save(code_dataset, "output_file.xml")
```

This will generate an XML file (`output_file.xml`) containing all your codes, fully ready to be imported into Hudl Sportscode.
