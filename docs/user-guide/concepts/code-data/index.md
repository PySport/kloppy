# Code data


Code (or "timeline") data is a time-coded feed that captures **key moments during a match, often manually tagged by analysts** using software such as [Hudl Sportscode](https://www.hudl.com/en_gb/products/sportscode), [Metrica Nexus](https://www.metrica-sports.com/metrica-nexus) or [Nacsport](https://www.nacsport.com/) while reviewing game footage. These key moments are defined by "labels" or "codes" (e.g., Pass, Shot, Counter) and are usually associated with a start and end time, and optional metadata like players involved, outcomes or field location.

Code data is typically used within coaching setups, and unlike structured feeds from event data providers like StatsBomb or Opta, it is highly customizable. Teams can define their own coding templates, tag schemes, and event taxonomies.

In the Hudl Sportscode XML format, a raw code that annotates a pass might look like this:

```xml
<instance>
    <ID>P1</ID>
    <start>3.6</start>
    <end>9.7</end>
    <code>PASS</code>
    <label>
        <group>Team</group>
        <text>France</text>
    </label>
    <label>
        <group>Player</group>
        <text>Antoine Griezmann</text>
    </label>
    <label>
        <group>Packing.Value</group>
        <text>1</text>
    </label>
    <label>
        <group>Receiver</group>
        <text>Tchouaméni</text>
    </label>
</instance>
```

This snippet defines:

- A pass event (`<code>PASS</code>`) with ID `P1`,
- Starting at 3.6 seconds and ending at 9.7 seconds,
- Tagged with team, player, packing value, and the receiving player.

In Kloppy, this XML instance would be parsed into a [`Code`][kloppy.domain.Code] object.

```python
from kloppy.domain import Code

Code(
    code_id="P1",
    timestamp=180.12,
    end_timestamp=182.67,
    code="Pass",
    labels={
      "team": "France",
      "player": "Antoine Griezmann",
      "receiver": "Tchouaméni",
      "Packing.Value": "1",
    }
)
```

A [`Code`][kloppy.domain.Code] object has the following fields:

- `code_id`: A unique identifier for the code.
- `timestamp`: The event’s start time in seconds.
- `end_timestamp`: The event’s end time in seconds.
- `code`: The type of event (e.g., `Pass`).
- `labels`: A dictionary of metadata fields extracted from `<label>` tags, grouped by their `group` names.

This abstraction allows Kloppy to work with various code data formats in a unified, structured way.
