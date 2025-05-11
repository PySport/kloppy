# Querying data
Oftentimes, not all data in a match is relevant. The goal of the analysis might be to investigate a certain time window, set of events, game phase, or tactical pattern.
Therefore, kloppy provides a number of tools to query and filter match data efficiently.

## Selecting events or frames
Kloppy provides a number of utility functions to extract specific events or frames based on a variety of criteria, such as:

- **Event type** – select only passes, shots, duels, etc.
- **Time window** – isolate moments before or after a key event.
- **Players or teams** – focus on data related to particular players or teams.
- **Spatial constraints** – filter events that occur in specific pitch areas.

See [Selecting Events]() for practical examples and common use cases.
## Pattern matching

Sometimes it’s not individual events that matter, but patterns: sequences of events that together signify a tactic or strategy (e.g., a high press, counterattack, or overlapping run).

Kloppy's `event_pattern_matching` module includes tools to define and search for these patterns. Read more in [Pattern Matching]() to see how to define, search, and iterate over tactical patterns.
