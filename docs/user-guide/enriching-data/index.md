# Enriching event data with state information

!!! example "TODO"

    While working with event data, it can be helpful to include contextual game state information such as the current score, the players on the pitch, or the team formation. In kloppy, you can use the [`.add_state()`][kloppy.domain.EventDataset.add_state] method to enrich event data with different types of state: `score`, `lineup`, and `formation`.
