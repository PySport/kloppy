# Querying data
Oftentimes, not all data in a match is relevant. The goal of the analysis might be to investigate a certain time window, set of events, game phase, or tactical pattern. Therefore, kloppy provides a number of tools to query and filter match data efficiently.

## Selecting events or frames
Kloppy provides a number of utility functions to select specific events or frames based on a variety of criteria, such as:

- **Event type** – select only passes, shots, duels, etc.
- **Time window** – isolate moments before or after a key event.
- **Players or teams** – focus on data related to particular players or teams.
- **Spatial constraints** – filter events that occur in specific pitch areas.

See [Selections](./selections/index.md) for practical examples and common use cases.
## Pattern matching

Sometimes it’s not individual events that matter, but patterns: sequences of events that together signify a tactic or strategy (e.g., a high press, counterattack, or build-up sequence).

Kloppy's `event_pattern_matching` module includes tools to define and search for such patterns. Read more in [Pattern Matching](./pattern-matching/index.md) to see how to define, search, and iterate over tactical patterns.
