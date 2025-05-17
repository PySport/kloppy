# Metadata

Metadata is contextual information that describes or helps to understand the actual (event or tracking) data. In kloppy, each dataset has a [`.metadata`][kloppy.domain.Dataset.metadata] attribute that keeps track of this contextual information, encapsulated in a [`Metadata`][kloppy.domain.Metadata] entity.

Broadly speaking, metadata in kloppy can be divided into two categories:

1. **Match Sheet Data** – Information about the match itself, such as teams, players, date, and score.
2. **Technical Specifications** – Details about how the data was collected, including pitch dimensions, coordinate systems, frame rate, and data provider.


## Match sheet data

Match sheet metadata refers to official match-related information. This typically includes team lineups, match officials, date and time, and key match events such as goals and disciplinary actions. This information provides the context necessary to understand what happened in a match and who was involved.


| **Attribute**         | **Type**            | **Optional** | **Description**                                                                                         |
|-----------------------|---------------------|--------------|---------------------------------------------------------------------------------------------------------|
| [`game_id`][kloppy.domain.Metadata.game_id]       | str                              | Yes | Game ID from the data provider. |
| [`date`][kloppy.domain.Metadata.date]             | datetime                         | Yes | Date the match took place. |
| [`game_week`][kloppy.domain.Metadata.game_week]   | str                              | Yes | 	Match day or competition stage (e.g., "8th Finals"). |
| [`periods`][kloppy.domain.Metadata.periods]       | [`Period`][kloppy.domain.Period] | No  | List of match periods. |
| [`teams`][kloppy.domain.Metadata.teams]           | [`Team`][kloppy.domain.Team]     | No  | List containing home team and away team metadata. |
| [`officials`][kloppy.domain.Metadata.officials]   | [`Official`][kloppy.domain.Official]   | Yes | List of match officials (i.e., referees). |
| [`score`][kloppy.domain.Metadata.score]           | [`Score`][kloppy.domain.Score]   | Yes | Final score of the match. |
| [`home_coach`][kloppy.domain.Metadata.home_coach] | str                              | Yes | Name of the home team's coach. |
| [`away_coach`][kloppy.domain.Metadata.away_coach] | str                              | Yes | Name of the away team's coach. |
| [`attributes`][kloppy.domain.Metadata.attributes] | Dict                             | Yes | Additional metadata such as stadium, weather, or attendance (if available). |



## Technical specifications

Technical metadata relates to how the data was collected, processed, and structured. This includes details like the coordinate system used, data provider, pitch dimensions, and tracking frame rate. This metadata is crucial for correctly interpreting the data.


| **Attribute**         | **Type**            | **Optional** | **Description**                                                                                         |
|-----------------------|---------------------|--------------|---------------------------------------------------------------------------------------------------------|
| [`provider`][kloppy.domain.Metadata.provider] | [`Provider`][kloppy.domain.Provider] | No | The data provider/vendor.|
| [`coordinate_system`][kloppy.domain.Metadata.coordinate_system] | [`CoordinateSystem`][kloppy.domain.CoordinateSystem] | No | The coordinate system used.|
| [`pitch_dimensions`][kloppy.domain.Metadata.pitch_dimensions] | [`PitchDimensions`][kloppy.domain.PitchDimensions] | No | Dimensions of the pitch.|
| [`orientation`][kloppy.domain.Metadata.orientation] | [`Orientation`][kloppy.domain.Orientation] | No | The attacking direction of each team.|
| [`flags`][kloppy.domain.Metadata.flags] | [`DatasetFlag`][kloppy.domain.DatasetFlag] | No | Flags describing what optional data is available.|
| [`frame_rate`][kloppy.domain.Metadata.frame_rate] | float | Yes | The frame rate (in Hertz) at which the data was recorded. Only for tracking data.|
